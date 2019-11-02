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

import json
import boto3

from datetime import datetime

from bai_kafka_utils.events import MetricsEvent, Status
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer, metrics_json_deserializer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name

from cloudwatch_exporter import SERVICE_NAME, __version__, service_logger

CLOUDWATCH_MAX_DIMENSIONS = 10

NOT_EXPORTED_LABELS = ["action-id", "parent-action-id", "client-id", "dashboard-name", "region"]

logger = service_logger.getChild(__name__)


class CloudWatchExporterService(KafkaService):
    @staticmethod
    def _check_message_belongs_to_topic(msg, topic):
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
        # Use labels seperate from event object so that function can be used by SM jobs as well
        labels = event.labels
        # Default region for Anubis is us-east-1
        if "region" not in event.labels:
            event.labels["region"] = "us-east-1"
        check_dashboard(self.cloudwatch_client, labels, event.name)

    def cleanup(self):
        pass


def check_dashboard(cloudwatch_client, labels, metric_name):
    """
    Checks if dashboard custom-parameter has been set. Will check if dashboard-name exists already,
    if so will call update
    If dashboard-name doesn't exist in dashboards will create dashboard with that name
    :param cloudwatch_client: Boto3 Cloudwatch_client passed in from caller
    :param labels: Metric info passed from toml file, always contains task_name and dashboard-name
    :param metric_name: Name of the metric in cloudwatch
    :return: N/A
    """
    if "dashboard-name" in labels:
        pre_existing_dashboard = False
        existing_dashboards = cloudwatch_client.list_dashboards()
        for dashboard in existing_dashboards["DashboardEntries"]:
            if dashboard["DashboardName"] == labels["dashboard-name"]:
                pre_existing_dashboard = True
        if pre_existing_dashboard:
            logger.info("Updating existing dashboard")
            update_dashboard(cloudwatch_client, labels, metric_name)
        else:
            logger.info("Creating new dashboard")
            create_dashboard(cloudwatch_client, labels, metric_name)
    else:
        logger.info("Dashboard-name not specified")


def update_dashboard(cloudwatch_client, labels, metric_name):
    """
    Updates dashboard with specified dashboard-name and places specified metric from labels/metric_name
    :param cloudwatch_client: Boto3 Cloudwatch_client passed in from caller
    :param labels: Metric info passed from toml file, always contains task_name and dashboard-name
    :param metric_name: Name of the metric in cloudwatch
    :return: N/A
    """
    dashboard = cloudwatch_client.get_dashboard(DashboardName=labels["dashboard-name"])
    dashboard_body = json.loads(dashboard["DashboardBody"])
    metric = create_dashboard_metric(labels, metric_name)
    # If exact metric specification is already in Dashboard don't add it again
    for widget in dashboard_body["widgets"]:
        properties = widget["properties"]
        if "metrics" in properties and properties["metrics"][0] == metric:
            logger.info("Metric is already in dashboard")
            return
    dashboard_body["widgets"].append(
        {
            "type": "metric",
            "properties": {
                "metrics": [metric],
                "region": labels["region"],
                "title": labels["task_name"],
                "period": 86400,
            },
        }
    )
    updated_dashboard_body = json.dumps(dashboard_body)
    logger.info(updated_dashboard_body)
    # Log return value from put_dashboard, contains information about success of method call
    ret_val = cloudwatch_client.put_dashboard(
        DashboardName=labels["dashboard-name"], DashboardBody=updated_dashboard_body
    )
    logger.info(ret_val)


def create_dashboard(cloudwatch_client, labels, metric_name):
    """
    Creates dashboard with specified dashboard-name and places specified metric from labels/metric_name
    :param cloudwatch_client: Boto3 Cloudwatch_client passed in from caller
    :param labels: Metric info passed from toml file, always contains task_name and dashboard-name
    :param metric_name: Name of the metric in cloudwatch
    :return: N/A
    """
    metric = create_dashboard_metric(labels, metric_name)
    new_dashboard = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [metric],
                    "region": labels["region"],
                    "title": labels["task_name"],
                    "period": 86400,
                },
            }
        ]
    }
    dashboard_as_json = json.dumps(new_dashboard)
    logger.info(dashboard_as_json)
    # Log return value from put_dashboard, contains information about success of method call
    ret_val = cloudwatch_client.put_dashboard(DashboardName=labels["dashboard-name"], DashboardBody=dashboard_as_json)
    logger.info(ret_val)


def create_dashboard_metric(labels, metric_name):
    """
    Creates metric list using labels and metrics name to identify the metric from cloudwatch to be used in the Dashboard
    :param labels: Metric info passed from toml file, always contains task_name and dashboard-name
    :param metric_name: Name of the metric in cloudwatch
    :return: Metric list populated with metric_name and all labels key/value pairs provided by toml
    """
    metric = ["ANUBIS/METRICS", metric_name]
    for name, val in labels.items():
        if name not in NOT_EXPORTED_LABELS:
            metric.append(name)
            metric.append(val)
    return metric


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
