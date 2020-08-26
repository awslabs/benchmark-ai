import kafka

from unittest.mock import MagicMock
from datetime import datetime
from cloudwatch_exporter.cloudwatch_exporter import (
    CloudWatchExporterService,
    CloudWatchExporterHandler,
    create_service,
    create_dashboard_metric,
)

NOT_EXPORTED_LABELS = ["action-id", "parent-action-id", "client-id", "dashboard-name", "region"]


def test_create_service(mocker, kafka_service_config):
    kafka_producer_class = mocker.patch.object(kafka, "KafkaProducer")
    kafka_consumer_class = mocker.patch.object(kafka, "KafkaConsumer")
    mock_create_consumer = mocker.patch(
        "cloudwatch_exporter.cloudwatch_exporter.create_kafka_consumer",
        return_value=(kafka_consumer_class),
        autospec=True,
    )
    mock_create_producer = mocker.patch(
        "cloudwatch_exporter.cloudwatch_exporter.create_kafka_producer",
        return_value=(kafka_producer_class),
        autospec=True,
    )

    service = create_service(kafka_service_config)

    assert isinstance(service, CloudWatchExporterService)
    mock_create_consumer.assert_called_once()
    mock_create_producer.assert_called_once()


def test_handle_event(mocker, metrics_event, mock_kafka_service):
    mock_boto_cloudwatch = MagicMock()
    mock_boto_cloudwatch.put_metric_data = MagicMock()
    mocker.patch("cloudwatch_exporter.cloudwatch_exporter.boto3.client", return_value=mock_boto_cloudwatch)

    cw_exporter_handler = CloudWatchExporterHandler()
    cw_exporter_handler.handle_event(metrics_event, mock_kafka_service)

    expected_dimensions = [
        {"Name": name, "Value": val} for name, val in metrics_event.labels.items() if name not in NOT_EXPORTED_LABELS
    ]
    mock_boto_cloudwatch.put_metric_data.assert_called_with(
        MetricData=[
            {
                "MetricName": metrics_event.name,
                "Dimensions": expected_dimensions,
                "Unit": "None",
                "Value": float(metrics_event.value),
                "StorageResolution": 1,
                "Timestamp": datetime.fromtimestamp(metrics_event.timestamp / 1000),
            }
        ],
        Namespace="ANUBIS/METRICS",
    )


def test_put_metric_data_with_string_value_in_event_is_called_with_float(mocker, metrics_event, mock_kafka_service):
    metric_value_str = "10"
    metrics_event.value = metric_value_str

    mock_boto_cloudwatch = MagicMock()
    mock_boto_cloudwatch.put_metric_data = MagicMock()
    mocker.patch("cloudwatch_exporter.cloudwatch_exporter.boto3.client", return_value=mock_boto_cloudwatch)

    cw_exporter_handler = CloudWatchExporterHandler()
    cw_exporter_handler.handle_event(metrics_event, mock_kafka_service)

    args, kwargs = mock_boto_cloudwatch.put_metric_data.call_args_list[0]
    metric_data = kwargs["MetricData"][0]
    assert metric_data["Value"] == 10.0


def test_create_dashboard_metric(mocker, metrics_event, mock_kafka_service):
    created_dashboard_metric = [
        "ANUBIS/METRICS",
        "METRIC",
        "LABEL",
        "VALUE",
        "task_name",
        "test_task",
    ]
    assert create_dashboard_metric(metrics_event.labels, metrics_event.name) == created_dashboard_metric
