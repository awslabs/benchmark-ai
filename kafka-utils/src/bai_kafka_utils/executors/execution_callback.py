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
import abc
import logging

from typing import Dict, List, Optional, Any

from bai_kafka_utils.events import (
    FetcherBenchmarkEvent,
    ExecutorPayload,
    ExecutorBenchmarkEvent,
    create_from_object,
    Status,
    BenchmarkJob,
)
from bai_kafka_utils.executors.descriptor import SINGLE_RUN_SCHEDULING
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceCallbackException

logger = logging.getLogger(__name__)


class ExecutionEngine(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def run(self, event: FetcherBenchmarkEvent) -> BenchmarkJob:
        pass

    @abc.abstractmethod
    def cancel(self, client_id: str, action_id: str, cascade: bool = False) -> Optional[Any]:
        """
        Attempts to delete resources related to the supplied action_id
        :param client_id: The client requesting the deletion
        :param action_id: The action id of the resources to be deleted
        :param cascade:  Whether or not to cascade the deletion to resources created by the resources related to
        "action_id". E.g. if a the action id related to a scheduled (periodic) benchmark, if "cascade" is True,
        any spawned benchmarks will also be deleted.
        :return: An optional and implementation dependent arbitrary object carrying information regarding the
        underlying deletion commands. This should be used for additional debug information.
        :raises: ExecutionEngineException in case there is an error deleting the resources.
        :raises: NoResourcesFoundException in case no resources for the supplied action_id could be found
        """
        pass


class ExecutionEngineException(Exception):
    pass


class NoResourcesFoundException(ExecutionEngineException):
    def __init__(self, action_id: str):
        super().__init__(f"No resources found for '{action_id}'")


class ExecutorEventHandler(KafkaServiceCallback):
    DEFAULT_ENGINE = "default"

    def __init__(
        self, execution_engines: Dict[str, ExecutionEngine], valid_execution_engines: List[str], producer_topic: str
    ):
        self.producer_topic = producer_topic
        self.execution_engines = execution_engines
        self.valid_execution_engines = set(valid_execution_engines)
        # Some engine is default for sure
        self.valid_execution_engines.add(ExecutorEventHandler.DEFAULT_ENGINE)

    def handle_event(self, event: FetcherBenchmarkEvent, kafka_service: KafkaService):

        # Only handle single run benchmarks
        if not ExecutorEventHandler.is_single_run(event):
            logging.debug(f"Ignoring non single-run event: {event}")
            return

        engine_id = ExecutorEventHandler.get_engine_id(event)
        engine = self.execution_engines.get(engine_id)

        if not engine:
            # Ok. I've failed, but may be another service can have this engine
            if engine_id in self.valid_execution_engines:
                logging.info(f"{engine_id} is whitelisted, but not present here. Nothing to do")
            else:
                # It's really something weird
                logging.warning(f"Unknown engine {engine_id}")
            return

        try:
            kafka_service.send_status_message_event(event, Status.PENDING, "Processing benchmark submission request...")
            job = engine.run(event)
        except ExecutionEngineException as e:
            logger.exception("Engine throws exception")
            kafka_service.send_status_message_event(event, Status.ERROR, str(e))
            raise KafkaServiceCallbackException from e

        payload = ExecutorPayload.create_from_fetcher_payload(event.payload, job)

        response_event = create_from_object(ExecutorBenchmarkEvent, event, payload=payload)

        kafka_service.send_status_message_event(response_event, Status.SUCCEEDED, "Benchmark successfully created...")
        kafka_service.send_event(response_event, topic=self.producer_topic)

    @staticmethod
    def get_engine_id(event):
        return event.payload.toml.contents.get("info", {}).get("execution_engine", ExecutorEventHandler.DEFAULT_ENGINE)

    @staticmethod
    def is_single_run(event):
        scheduling = event.payload.toml.contents.get("info", {}).get("scheduling", SINGLE_RUN_SCHEDULING)
        return scheduling == SINGLE_RUN_SCHEDULING

    def cleanup(self):
        pass
