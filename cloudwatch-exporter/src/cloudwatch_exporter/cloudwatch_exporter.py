import boto3

from datetime import datetime
from itertools import islice

from bai_kafka_utils.events import MetricsEvent, Status
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer, metrics_json_deserializer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name

from cloudwatch_exporter import SERVICE_NAME, __version__, service_logger

CLOUDWATCH_MAX_DIMENSIONS = 10

logger = service_logger.getChild(__name__)


class CloudWatchExporterService(KafkaService):
    @staticmethod
    def _check_mesage_belongs_to_topic(msg, topic):
        # Suppress this check for metrics events since they don't have a 'type' field
        pass

    def send_status_message_event(self, handled_event: MetricsEvent, status: Status, msg: str):
        # We also don't need to send a status event for each metric we consume
        logger.debug(f"Exporting metric {handled_event}")


class CloudWatchExporterHandler(KafkaServiceCallback):
    def __init__(self):
        self.cloudwatch_client = boto3.client("cloudwatch")

    def handle_event(self, event: MetricsEvent, kafka_service: KafkaService):
        logger.info(event)
        if len(event.labels) > CLOUDWATCH_MAX_DIMENSIONS:
            logger.warn(
                f"Too many labels for metric. Found {len(event.labels)}, maximum allowed by CloudWatch"
                f" is {CLOUDWATCH_MAX_DIMENSIONS}. The exceeding ones have not been exported."
            )
        dimensions = [
            {"Name": name, "Value": val} for name, val in islice(event.labels.items(), CLOUDWATCH_MAX_DIMENSIONS)
        ]
        dims = []
        for item in dimensions:
            if item["Name"] == "action-id" or item["Name"] == "client-id":
                continue
            else:
                dims.append(item)
        # Put custom metrics
        self.cloudwatch_client.put_metric_data(
            MetricData=[
                {
                    "MetricName": event.name,
                    "Dimensions": dims,
                    "Unit": "None",
                    "Value": float(event.value),
                    "Timestamp": datetime.fromtimestamp(event.timestamp / 1000),
                    "StorageResolution": 1,
                }
            ],
            Namespace="ANUBIS/METRICS",
        )

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

    return CloudWatchExporterService(
        name=SERVICE_NAME,
        version=__version__,
        callbacks=callbacks,
        kafka_consumer=consumer,
        kafka_producer=producer,
        pod_name=get_pod_name(),
        status_topic=common_kafka_cfg.status_topic,
    )
