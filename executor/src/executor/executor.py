#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import logging

from bai_kafka_utils.events import FetcherBenchmarkEvent, Status
from bai_kafka_utils.executors.descriptor import SINGLE_RUN_SCHEDULING
from bai_kafka_utils.executors.execution_callback import ExecutorEventHandler, ExecutionEngineException
from bai_kafka_utils.executors.executor_service import create_executor_service
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaServiceCallbackException

from executor import SERVICE_NAME, __version__
from executor.config import ExecutorConfig
from executor.k8s_execution_engine import K8SExecutionEngine

logger = logging.getLogger(SERVICE_NAME)


class ScheduledBenchmarkExecutorEventHandler(KafkaServiceCallback):
    DEFAULT_ENGINE = "default"

    def __init__(self, k8s_execution_engine: K8SExecutionEngine):
        self.k8s_execution_engine = k8s_execution_engine

    def handle_event(self, event: FetcherBenchmarkEvent, kafka_service: KafkaService):
        # Only handle scheduled benchmarks
        if ScheduledBenchmarkExecutorEventHandler.is_single_run(event):
            logging.debug(f"Ignoring event non scheduled benchmark event: {event}")
            return

        try:
            kafka_service.send_status_message_event(
                event, Status.PENDING, "Processing scheduled benchmark submission request..."
            )
            job = self.k8s_execution_engine.schedule(event)
        except ExecutionEngineException as e:
            logger.exception("Engine throws exception")
            kafka_service.send_status_message_event(event, Status.ERROR, str(e))
            raise KafkaServiceCallbackException from e

        kafka_service.send_status_message_event(
            event, Status.SUCCEEDED, f"Scheduled benchmark successfully submitted with job id {job.id}"
        )

    @staticmethod
    def is_single_run(event):
        scheduling = event.payload.toml.contents.get("info", {}).get("scheduling", SINGLE_RUN_SCHEDULING)
        return scheduling == SINGLE_RUN_SCHEDULING

    def cleanup(self):
        pass


def create_executor(common_kafka_cfg: KafkaServiceConfig, executor_config: ExecutorConfig) -> KafkaService:
    k8s_engine = K8SExecutionEngine(executor_config)
    execution_engines = {ExecutorEventHandler.DEFAULT_ENGINE: k8s_engine, K8SExecutionEngine.ENGINE_ID: k8s_engine}

    kafka_service = create_executor_service(SERVICE_NAME, __version__, common_kafka_cfg, execution_engines)

    # Add Scheduled Benchmark Handler
    scheduled_benchmark_handler = ScheduledBenchmarkExecutorEventHandler(k8s_engine)
    kafka_service.add_callback(scheduled_benchmark_handler, common_kafka_cfg.consumer_topic)

    return kafka_service
