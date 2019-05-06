from unittest.mock import patch, MagicMock, ANY

import pytest

import bai_kafka_utils
from bai_kafka_utils.events import BenchmarkEvent, BenchmarkPayload
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer, WrongBenchmarkEventTypeException
from bai_kafka_utils.utils import DEFAULT_ENCODING

BOOTSTRAP_SERVERS = ["kafka_node"]
TOPIC = "TOPIC"
GROUP_ID = "GROUP_ID"

INVALID_JSON = "INVALID".encode(DEFAULT_ENCODING)
WRONG_SCHEMA_JSON = '{"foo":"bar"}'.encode(DEFAULT_ENCODING)


@patch.object(bai_kafka_utils.kafka_client.kafka, "KafkaConsumer")
def test_kafka_consumer_pass_through(mockKafkaConsumer):
    create_kafka_consumer(BOOTSTRAP_SERVERS, GROUP_ID, TOPIC, BenchmarkEvent)
    mockKafkaConsumer.assert_called_with(
        TOPIC, bootstrap_servers=BOOTSTRAP_SERVERS, group_id=GROUP_ID, value_deserializer=ANY
    )


@patch.object(bai_kafka_utils.kafka_client.kafka, "KafkaConsumer")
def test_kafka_consumer_handles_invalid_format(mockKafkaConsumer):
    create_kafka_consumer(BOOTSTRAP_SERVERS, GROUP_ID, TOPIC, BenchmarkEvent)
    deserializer = get_deserializer(mockKafkaConsumer)

    res = deserializer(INVALID_JSON)
    assert not res


@patch.object(bai_kafka_utils.kafka_client.kafka, "KafkaConsumer")
def test_kafka_consumer_handles_wrong_schema(mockKafkaConsumer):
    create_kafka_consumer(BOOTSTRAP_SERVERS, GROUP_ID, TOPIC, BenchmarkEvent)
    deserializer = get_deserializer(mockKafkaConsumer)

    res = deserializer(WRONG_SCHEMA_JSON)
    assert not res


@patch.object(bai_kafka_utils.kafka_client.kafka, "KafkaProducer")
def test_kafka_producer_pass_through(mockKafkaProducer):
    create_kafka_producer(BOOTSTRAP_SERVERS)
    mockKafkaProducer.assert_called_with(bootstrap_servers=BOOTSTRAP_SERVERS, value_serializer=ANY)


def test_wrong_event_type():
    with pytest.raises(WrongBenchmarkEventTypeException):
        create_kafka_consumer(BOOTSTRAP_SERVERS, GROUP_ID, TOPIC, BenchmarkPayload)


def get_deserializer(mock: MagicMock):
    kwargs = mock.call_args[1]
    return kwargs["value_deserializer"]
