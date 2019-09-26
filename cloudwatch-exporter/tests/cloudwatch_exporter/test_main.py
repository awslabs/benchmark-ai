from unittest.mock import Mock

from bai_kafka_utils.kafka_service import KafkaServiceConfig, DEFAULT_REPLICATION_FACTOR, DEFAULT_NUM_PARTITIONS

BOOTSTRAP_SERVERS = ["K1", "K2"]
LOGGING_LEVEL = "WARN"
CONSUMER_TOPIC = "IN"
PRODUCER_TOPIC = "OUT"
STATUS_TOPIC = "STATUS_TOPIC"
CMD_RETURN_TOPIC = "CMD_RETURN"
CMD_SUBMIT_TOPIC = "CMD_SUBMIT"
BOOTSTRAP_SERVERS_ARG = ",".join(BOOTSTRAP_SERVERS)


def test_main(mocker):
    mock_create_service = mocker.patch("cloudwatch_exporter.cloudwatch_exporter.create_service")
    mock_cloudwatch_service = Mock()
    mock_create_service.return_value = mock_cloudwatch_service
    from cloudwatch_exporter.__main__ import main

    main(
        f" --consumer-topic {CONSUMER_TOPIC} "
        f" --producer-topic {PRODUCER_TOPIC} "
        f" --status-topic {STATUS_TOPIC} "
        f" --cmd-return-topic {CMD_RETURN_TOPIC} "
        f" --cmd-submit-topic {CMD_SUBMIT_TOPIC} "
        f" --bootstrap-servers {BOOTSTRAP_SERVERS_ARG} "
        f" --logging-level {LOGGING_LEVEL} "
    )

    expected_common_kafka_cfg = KafkaServiceConfig(
        consumer_topic=CONSUMER_TOPIC,
        producer_topic=PRODUCER_TOPIC,
        cmd_return_topic=CMD_RETURN_TOPIC,
        cmd_submit_topic=CMD_SUBMIT_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        logging_level=LOGGING_LEVEL,
        status_topic=STATUS_TOPIC,
        replication_factor=min(DEFAULT_REPLICATION_FACTOR, len(BOOTSTRAP_SERVERS)),
        num_partitions=DEFAULT_NUM_PARTITIONS,
    )

    mock_create_service.assert_called_with(expected_common_kafka_cfg)
    mock_cloudwatch_service.run_loop.assert_called_once()
