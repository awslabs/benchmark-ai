import json

import boto3

from datetime import datetime

from bai_kafka_utils.events import MetricsEvent, Status
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer, metrics_json_deserializer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name

from cloudwatch_exporter import SERVICE_NAME, __version__, service_logger

CLOUDWATCH_MAX_DIMENSIONS = 10

NOT_EXPORTED_LABELS = ["action-id", "parent-action-id", "client-id", "dashboard-name"]

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
        dimensions = [
            {"Name": name, "Value": val} for name, val in event.labels.items() if name not in NOT_EXPORTED_LABELS
        ]
        if len(dimensions) > CLOUDWATCH_MAX_DIMENSIONS:
            dimensions = dimensions[:10]
            logger.warn(
                f"Too many labels for metric. Found {len(event.labels)}, maximum allowed by CloudWatch"
                f" is {CLOUDWATCH_MAX_DIMENSIONS}. The exceeding ones have not been exported."
            )

        # Put metrics
        self.cloudwatch_client.put_metric_data(
            MetricData=[
                {
                    "MetricName": event.name,
                    "Dimensions": dimensions,
                    "Unit": "None",
                    "Value": float(event.value),
                    "Timestamp": datetime.fromtimestamp(event.timestamp / 1000),
                    "StorageResolution": 1,
                }
            ],
            Namespace="ANUBIS/METRICS",
        )
        logger.info("BEfore if")
        if "dashboard-name" in event.labels:
            logger.info("IF worked")
            pre_existing_dashboard = False
            existing_dashboards = self.cloudwatch_client.list_dashboards()
            for dashboard in existing_dashboards["DashboardEntries"]:
                if dashboard["DashboardName"] == event.labels["dashboard-name"]:
                    pre_existing_dashboard = True
            if pre_existing_dashboard:
                logger.info("We made it to update")
                self.update_dashboard(event)
            else:
                logger.info("We made it to create")
                self.create_dashboard(event)

    def update_dashboard(self, event):
        dashboard = self.cloudwatch_client.get_dashboard(DashboardName=event.labels["dashboard-name"])
        dashboard_body = json.loads(dashboard["DashboardBody"])
        metric = ["ANUBIS/METRICS", event.name]
        for name, val in event.labels.items():
            if name not in NOT_EXPORTED_LABELS:
                metric.append(name)
                metric.append(val)
        dashboard_body["widgets"].append(
            {
                "type": "metric",
                "properties": {
                    "metrics": [metric],
                    "region": "us-east-1",
                    "title": event.labels["task_name"],
                    "period": 86400,
                },
            }
        )
        updated_dashboard_body = json.dumps(dashboard_body)
        retVal = self.cloudwatch_client.put_dashboard(
            DashboardName=event.labels["dashboard-name"], DashboardBody=updated_dashboard_body
        )
        logger.info(retVal)

    def create_dashboard(self, event):
        metric = ["ANUBIS/METRICS", event.name]
        for name, val in event.labels.items():
            if name not in NOT_EXPORTED_LABELS:
                metric.append(name)
                metric.append(val)
        new_dashboard = {
            "widgets": [
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [metric],
                        "region": "us-east-1",
                        "title": event.labels["task_name"],
                        "period": 86400,
                    },
                }
            ]
        }
        dashboard_as_json = json.dumps(new_dashboard)
        retVal = self.cloudwatch_client.put_dashboard(
            DashboardName=event.labels["dashboard-name"], DashboardBody=dashboard_as_json
        )
        logger.info(retVal)

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
