from bai_kafka_utils.kafka_service import KafkaServiceConfig
from bai_kafka_utils.kafka_service_args import get_kafka_service_config

LOGGING_LEVEL = "DEBUG"

MOCK_SERVICE_NAME = "AMAZING_SOFT"
MOCK_CONSUMER_GROUP_ID = "GROUP_ID"
MOCK_KAFKA1 = "kafka1:9092"
MOCK_KAFKA2 = "kafka2:9092"
MOCK_PRODUCER_TOPIC = "OUT_TOPIC"
MOCK_CONSUMER_TOPIC = "IN_TOPIC"
MOCK_STATUS_TOPIC = "STATUS_TOPIC"
CMD_SUBMIT_TOPIC = "CMD_SUBMIT"
CMD_RETURN_TOPIC = "CMD_RETURN"
MOCK_REPLICATION_FACTOR = 1
MOCK_NUM_PARTITIONS=42

MOCK_KAFKA_BOOTSTRAP_SERVERS = [MOCK_KAFKA1, MOCK_KAFKA2]

ARGS = f"""--bootstrap-servers={MOCK_KAFKA1},{MOCK_KAFKA2}
    --consumer-group-id={MOCK_CONSUMER_GROUP_ID}
    --consumer-topic={MOCK_CONSUMER_TOPIC}
    --producer-topic={MOCK_PRODUCER_TOPIC}
    --cmd-submit-topic {CMD_SUBMIT_TOPIC}
    --cmd-return-topic {CMD_RETURN_TOPIC}
    --status-topic={MOCK_STATUS_TOPIC}
    --logging-level={LOGGING_LEVEL}\
    --replication-factor={MOCK_REPLICATION_FACTOR}
    --num-partitions={MOCK_NUM_PARTITIONS}
"""

EXPECTED_CONFIG = KafkaServiceConfig(
    bootstrap_servers=MOCK_KAFKA_BOOTSTRAP_SERVERS,
    consumer_group_id=MOCK_CONSUMER_GROUP_ID,
    consumer_topic=MOCK_CONSUMER_TOPIC,
    logging_level=LOGGING_LEVEL,
    producer_topic=MOCK_PRODUCER_TOPIC,
    status_topic=MOCK_STATUS_TOPIC,
    cmd_return_topic=CMD_RETURN_TOPIC,
    cmd_submit_topic=CMD_SUBMIT_TOPIC,
    replication_factor=MOCK_REPLICATION_FACTOR,
    num_partitions=MOCK_NUM_PARTITIONS
)


def test_happy_path_command_args():
    cfg = get_kafka_service_config(MOCK_SERVICE_NAME, ARGS)
    assert cfg == EXPECTED_CONFIG


def test_dont_fail_unrecognized():
    get_kafka_service_config(MOCK_SERVICE_NAME, ARGS + " -foo")
