from bai_kafka_utils.events import BenchmarkEvent
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name

from cloudwatch_exporter import SERVICE_NAME, __version__, service_logger

logger = service_logger.getChild(__name__)


class CloudWatchExporterHandler(KafkaServiceCallback):
    def __init__(self):
        pass

    def handle_event(self, event: BenchmarkEvent, kafka_service: KafkaService):
        logger.info(event)

    def cleanup(self):
        pass


def create_service(common_kafka_cfg: KafkaServiceConfig) -> KafkaService:
    callbacks = {common_kafka_cfg.consumer_topic: [CloudWatchExporterHandler()]}
    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, SERVICE_NAME)
    return KafkaService(
        name=SERVICE_NAME,
        version=__version__,
        callbacks=callbacks,
        kafka_consumer=consumer,
        kafka_producer=producer,
        pod_name=get_pod_name(),
        status_topic=common_kafka_cfg.status_topic,
    )
