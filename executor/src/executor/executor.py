import subprocess
import logging

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
from transpiler.descriptor import DescriptorError

logger = logging.getLogger(SERVICE_NAME)


JOB_ID_PREFIX = "benchmark-"


class ExecutorEventHandler(KafkaServiceCallback):
    def __init__(self, executor_config: ExecutorConfig, producer_topic: str):
        self.config = executor_config
        self.producer_topic = producer_topic

    def handle_event(self, event: FetcherBenchmarkEvent, kafka_service: KafkaService):
        descriptor_contents = event.payload.toml.contents
        fetched_data_sources = event.payload.datasets
        job_id = JOB_ID_PREFIX + event.action_id

        try:
            yaml = create_job_yaml_spec(descriptor_contents, self.config, fetched_data_sources, job_id, event=event)
            self._kubernetes_apply(yaml)
        except DescriptorError as e:
            logger.exception(f"Error parsing descriptor file")
            kafka_service.send_status_message_event(event, Status.ERROR, str(e))
            return
        except subprocess.CalledProcessError as e:
            logger.exception(f"Error executing benchmark")
            kafka_service.send_status_message_event(event, Status.ERROR, str(e))
            return

        response_event = self._create_response_event(event, job_id, yaml)
        kafka_service.send_status_message_event(
            response_event, Status.SUCCEEDED, f"Benchmark successfully submitted with job id {job_id}"
        )
        kafka_service.send_event(response_event, topic=self.producer_topic)

    def _kubernetes_apply(self, yaml: str):
        # Shelling out this command because the kubernetes python client does not have a good way to
        # call kubectl apply -f my_config.yaml (https://github.com/kubernetes-client/python/issues/387)
        # Specially https://github.com/kubernetes-client/python/pull/655 - CRDs not supported
        cmd = [self.config.kubectl, "apply", "-f", "-"]

        logger.info(f"Applying yaml file using command: {cmd}")
        result = subprocess.check_output(cmd, input=yaml.encode(DEFAULT_ENCODING))
        logger.info(f"Kubectl output: {result}")
        logger.info(f"Job submitted with yaml: \n {yaml}")

    def _create_response_event(self, input_event: FetcherBenchmarkEvent, job_id: str, yaml: str):
        try:
            job = BenchmarkJob(id=job_id, k8s_yaml=yaml)
            response_payload = ExecutorPayload.create_from_fetcher_payload(input_event.payload, job)
            return create_from_object(ExecutorBenchmarkEvent, input_event, payload=response_payload)
        except ValueError as e:
            logging.exception(f"Data type problem in the received event: {input_event}")
            raise KafkaServiceCallbackException from e

    def cleanup(self):
        pass


def create_executor(common_kafka_cfg: KafkaServiceConfig, executor_config: ExecutorConfig) -> KafkaService:

    callbacks = {
        common_kafka_cfg.consumer_topic: [ExecutorEventHandler(executor_config, common_kafka_cfg.producer_topic)]
    }

    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, SERVICE_NAME)

    pod_name = get_pod_name()

    return KafkaService(
        name=SERVICE_NAME,
        version=__version__,
        callbacks=callbacks,
        kafka_consumer=consumer,
        kafka_producer=producer,
        pod_name=pod_name,
        status_topic=common_kafka_cfg.status_topic,
    )
