from unittest.mock import patch, MagicMock

from configargparse import ArgParser, Namespace
from pytest import fixture

from bai_kafka_utils import kafka_client
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service_args import create_kafka_service_parser, BOOTSTRAP_SERVERS_ARG, \
    CONSUMER_GROUP_ID_ARG, CONSUMER_TOPIC_ARG, PRODUCER_TOPIC_ARG, LOGGING_LEVEL_ARG, BOOTSTRAP_SERVERS_ENV, \
    CONSUMER_GROUP_ID_ENV, CONSUMER_TOPIC_ENV, PRODUCER_TOPIC_ENV, LOGGING_LEVEL_ENV

LOGGING_LEVEL = "DEBUG"

MOCK_SERVICE_NAME = "AMAZING_SOFT"
MOCK_CONSUMER_GROUP_ID = "GROUP_ID"
MOCK_KAFKA1 = "kafka1:9092"
MOCK_KAFKA2 = "kafka2:9092"
MOCK_PRODUCER_TOPIC = "OUT_TOPIC"
MOCK_CONSUMER_TOPIC = "IN_TOPIC"

MOCK_KAFKA_BOOTSTRAP_SERVERS = [MOCK_KAFKA1, MOCK_KAFKA2]

ARGS = f'''{BOOTSTRAP_SERVERS_ARG}={MOCK_KAFKA1},{MOCK_KAFKA2}
    {CONSUMER_GROUP_ID_ARG}={MOCK_CONSUMER_GROUP_ID}
    {CONSUMER_TOPIC_ARG}={MOCK_CONSUMER_TOPIC}
    {PRODUCER_TOPIC_ARG}={MOCK_PRODUCER_TOPIC}
    {LOGGING_LEVEL_ARG}={LOGGING_LEVEL}'''

EXPECTED_ARGS = Namespace(bootstrap_servers=MOCK_KAFKA_BOOTSTRAP_SERVERS,
                          consumer_group_id=MOCK_CONSUMER_GROUP_ID,
                          consumer_topic=MOCK_CONSUMER_TOPIC,
                          logging_level=LOGGING_LEVEL,
                          producer_topic=MOCK_PRODUCER_TOPIC)


@fixture
def kafka_service_args_parser() -> ArgParser:
    return create_kafka_service_parser(MOCK_SERVICE_NAME)


# Trivial test to check if KafkaService imports something missing
def test_kafka_service_imports():
    from bai_kafka_utils.kafka_service_args import create_kafka_service_parser
    assert create_kafka_service_parser


def test_happy_path_command_args(kafka_service_args_parser: ArgParser):
    args = kafka_service_args_parser.parse_args(ARGS)
    assert args == EXPECTED_ARGS


def test_happy_path_env(kafka_service_args_parser: ArgParser):
    mock_env = {
        BOOTSTRAP_SERVERS_ENV: f"{MOCK_KAFKA1},{MOCK_KAFKA2}",
        CONSUMER_GROUP_ID_ENV: MOCK_CONSUMER_GROUP_ID,
        CONSUMER_TOPIC_ENV: MOCK_CONSUMER_TOPIC,
        PRODUCER_TOPIC_ENV: MOCK_PRODUCER_TOPIC,
        LOGGING_LEVEL_ENV: LOGGING_LEVEL
    }
    args = kafka_service_args_parser.parse_args("", env_vars=mock_env)
    assert args == EXPECTED_ARGS


@patch.object(kafka_client, "create_kafka_producer")
@patch.object(kafka_client, "create_kafka_consumer")
def test_args_match_attributes(mock_create_kafka_consumer, mock_create_kafka_producer,
                               kafka_service_args_parser: ArgParser):
    args = kafka_service_args_parser.parse_args(ARGS)
    mock_payload_type = MagicMock()
    create_kafka_consumer_producer(args, mock_payload_type)

    mock_create_kafka_consumer.assert_called_with(MOCK_KAFKA_BOOTSTRAP_SERVERS, MOCK_CONSUMER_GROUP_ID,
                                                  MOCK_CONSUMER_TOPIC, mock_payload_type)
    mock_create_kafka_producer.assert_called_with(MOCK_KAFKA_BOOTSTRAP_SERVERS)
