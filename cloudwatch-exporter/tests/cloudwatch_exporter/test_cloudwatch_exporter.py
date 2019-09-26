import kafka

from unittest.mock import MagicMock
from cloudwatch_exporter.cloudwatch_exporter import CloudWatchExporterService, CloudWatchExporterHandler, create_service


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

    expected_dimensions = [{"Name": name, "Value": val} for name, val in metrics_event.labels.items()]
    mock_boto_cloudwatch.put_metric_data.assert_called_with(
        MetricData=[
            {
                "MetricName": metrics_event.name,
                "Dimensions": expected_dimensions,
                "Unit": "None",
                "Value": metrics_event.value,
            }
        ],
        Namespace="ANUBIS/METRICS",
    )
