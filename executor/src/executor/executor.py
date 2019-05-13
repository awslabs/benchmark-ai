import subprocess
import logging
from typing import Tuple

from dacite import WrongTypeError

from executor import SERVICE_NAME, __version__
from executor.config import ExecutorConfig
from transpiler.bai_knowledge import create_job_yaml_spec
from bai_kafka_utils.events import (
    FetcherBenchmarkEvent,
    ExecutorPayload,
    BenchmarkJob,
    ExecutorBenchmarkEvent,
    create_from_object,
    Status,
)
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import (
    KafkaServiceCallback,
    KafkaService,
    KafkaServiceConfig,
    KafkaServiceCallbackException,
)
from bai_kafka_utils.utils import DEFAULT_ENCODING, get_pod_name

logger = logging.getLogger(SERVICE_NAME)


class ExecutorEventHandler(KafkaServiceCallback):
    def __init__(self, executor_config):
        self.executor_config = executor_config

    def handle_event(self, event: FetcherBenchmarkEvent, kafka_service: KafkaService):
        descriptor_contents = event.payload.toml.contents
        fetched_data_sources = event.payload.datasets

        yaml, job_id = create_job_yaml_spec(descriptor_contents, self.executor_config, fetched_data_sources)

        job_is_submitted, output = self._kubernetes_apply(yaml)

        if job_is_submitted:
            response_event = self._create_response_event(event, job_id, yaml)
            kafka_service.send_status_message_event(
                response_event, Status.SUBMITTED, f"Benchmark successfully submitted with job id {job_id}"
            )
            return response_event
        else:
            kafka_service.send_status_message_event(event, Status.ERROR, output)

    def _kubernetes_apply(self, yaml: str) -> Tuple[bool, str]:
        # Shelling out this command because the kubernetes python client does not have a good way to
        # call kubectl apply -f my_config.yaml (https://github.com/kubernetes-client/python/issues/387)
        # Specially https://github.com/kubernetes-client/python/pull/655 - CRDs not supported
        cmd = [self.executor_config.kubectl, "apply", "-f", "-"]

        try:
            logger.info(f"Applying yaml file using command: {cmd}")
            result = subprocess.check_output(cmd, input=yaml.encode(DEFAULT_ENCODING))
            logger.info(f"Kubectl output: {result}")
            logger.info(f"Job submitted with yaml: \n {yaml}")
            return True, result
        except subprocess.CalledProcessError as e:
            logger.exception(f"Error executing benchmark: {str(e)}")
            return False, e.output()

    def _create_response_event(self, input_event: FetcherBenchmarkEvent, job_id: str, yaml: str):
        try:
            job = BenchmarkJob(id=job_id, k8s_yaml=yaml)
            response_payload = ExecutorPayload.create_from_fetcher_payload(input_event.payload, job)
            return create_from_object(ExecutorBenchmarkEvent, input_event, payload=response_payload)
        except WrongTypeError as e:
            logging.exception("Data type problem in the received event")
            raise KafkaServiceCallbackException(str(e))

    def cleanup(self):
        pass


def create_executor(common_kafka_cfg: KafkaServiceConfig, executor_config: ExecutorConfig) -> KafkaService:

    callbacks = [ExecutorEventHandler(executor_config)]

    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, FetcherBenchmarkEvent)

    pod_name = get_pod_name()

    return KafkaService(
        SERVICE_NAME,
        __version__,
        common_kafka_cfg.producer_topic,
        callbacks,
        consumer,
        producer,
        pod_name,
        status_topic=common_kafka_cfg.status_topic,
    )
