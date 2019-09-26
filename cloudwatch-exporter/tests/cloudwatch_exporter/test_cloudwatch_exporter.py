import kafka

from cloudwatch_exporter.cloudwatch_exporter import CloudWatchExporterService, create_service


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
