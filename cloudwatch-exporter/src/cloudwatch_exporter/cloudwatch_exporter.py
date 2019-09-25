from bai_kafka_utils.events import MetricsEvent
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer, metrics_json_deserializer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name

from cloudwatch_exporter import SERVICE_NAME, __version__, service_logger

logger = service_logger.getChild(__name__)


class CloudWatchExporterHandler(KafkaServiceCallback):
    def __init__(self):
        pass

    def handle_event(self, event: MetricsEvent, kafka_service: KafkaService):
        logger.info(event)

    def cleanup(self):
        pass


def create_service(common_kafka_cfg: KafkaServiceConfig) -> KafkaService:
    callbacks = {common_kafka_cfg.consumer_topic: [CloudWatchExporterHandler()]}

    consumer = create_kafka_consumer(
        bootstrap_servers=common_kafka_cfg.bootstrap_servers,
        group_id=common_kafka_cfg.consumer_group_id,
        topics=[common_kafka_cfg.consumer_topic],
        value_deserializer=metrics_json_deserializer,
    )

    producer = create_kafka_producer(common_kafka_cfg.bootstrap_servers)

    return KafkaService(
        name=SERVICE_NAME,
        version=__version__,
        callbacks=callbacks,
        kafka_consumer=consumer,
        kafka_producer=producer,
        pod_name=get_pod_name(),
        status_topic=common_kafka_cfg.status_topic,
    )
