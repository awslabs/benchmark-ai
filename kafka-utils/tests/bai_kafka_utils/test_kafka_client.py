import pytest
from pytest import fixture
from unittest.mock import MagicMock, ANY

import bai_kafka_utils
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer, MAX_IDLE_TIME_MS
from bai_kafka_utils.utils import DEFAULT_ENCODING

ILLEGAL_UTF8_KEY = b"\xc3\x28"

CLIENT_ID_SERIALIZED = b"AA"

CLIENT_ID = "AA"

BOOTSTRAP_SERVERS = ["kafka_node"]
TOPIC = "TOPIC"
GROUP_ID = "GROUP_ID"

INVALID_JSON = "INVALID".encode(DEFAULT_ENCODING)
WRONG_SCHEMA_JSON = '{"foo":"bar"}'.encode(DEFAULT_ENCODING)


@fixture
def mock_kafka_consumer(mocker):
    return mocker.patch.object(bai_kafka_utils.kafka_client.kafka, "KafkaConsumer")


@fixture
def mock_kafka_producer(mocker):
    return mocker.patch.object(bai_kafka_utils.kafka_client.kafka, "KafkaProducer")


def test_kafka_consumer_pass_through(mock_kafka_consumer):
    create_kafka_consumer(BOOTSTRAP_SERVERS, GROUP_ID, [TOPIC])
    mock_kafka_consumer.assert_called_with(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        value_deserializer=ANY,
        key_deserializer=ANY,
        connections_max_idle_ms=MAX_IDLE_TIME_MS,
    )


def test_kafka_consumer_handles_invalid_format(mock_kafka_consumer):
    create_kafka_consumer(BOOTSTRAP_SERVERS, GROUP_ID, [TOPIC])
    deserializer = get_deserializer(mock_kafka_consumer)

    assert deserializer(INVALID_JSON) is None


def test_kafka_consumer_handles_wrong_schema(mock_kafka_consumer):
    create_kafka_consumer(BOOTSTRAP_SERVERS, GROUP_ID, [TOPIC])
    deserializer = get_deserializer(mock_kafka_consumer)

    assert deserializer(WRONG_SCHEMA_JSON) is None


@pytest.mark.parametrize(
    "serialized_key, expected_key", [(CLIENT_ID_SERIALIZED, CLIENT_ID), (None, None), (ILLEGAL_UTF8_KEY, None)]
)
def test_kafka_key_deserializer(mock_kafka_consumer, serialized_key, expected_key):
    create_kafka_consumer(BOOTSTRAP_SERVERS, GROUP_ID, [TOPIC])
    key_deserializer = get_key_deserializer(mock_kafka_consumer)

    assert expected_key == key_deserializer(serialized_key)


def test_kafka_key_deserializer_serializer(mock_kafka_consumer, mock_kafka_producer):
    create_kafka_consumer(BOOTSTRAP_SERVERS, GROUP_ID, [TOPIC])
    create_kafka_producer(BOOTSTRAP_SERVERS)

    key_deserializer = get_key_deserializer(mock_kafka_consumer)
    key_serializer = get_key_serializer(mock_kafka_producer)

    assert CLIENT_ID == key_deserializer(key_serializer(CLIENT_ID))


def test_kafka_producer_pass_through(mock_kafka_producer):
    create_kafka_producer(BOOTSTRAP_SERVERS)
    mock_kafka_producer.assert_called_with(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=ANY,
        key_serializer=ANY,
        connections_max_idle_ms=MAX_IDLE_TIME_MS,
    )


def test_kafka_key_serializer(mock_kafka_producer):
    create_kafka_producer(BOOTSTRAP_SERVERS)
    key_serializer = get_key_serializer(mock_kafka_producer)

    assert CLIENT_ID_SERIALIZED == key_serializer(CLIENT_ID)


def get_deserializer(mock: MagicMock):
    _, kwargs = mock.call_args
    return kwargs["value_deserializer"]


def get_key_serializer(mock: MagicMock):
    _, kwargs = mock.call_args
    return kwargs["key_serializer"]


def get_key_deserializer(mock: MagicMock):
    _, kwargs = mock.call_args
    return kwargs["key_deserializer"]
