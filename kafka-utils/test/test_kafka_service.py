import collections
import copy
import time
import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from kafka import KafkaConsumer, KafkaProducer
from pytest import fixture

from bai_kafka_utils.events import BenchmarkPayload, BenchmarkEvent, BenchmarkDoc, VisitedService
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceCallback

MOCK_UUID = "4B545FB7-66B6-4C24-A681-7F1625313257"

OUT_TOPIC = 'OUT_TOPIC'

SERVICE_NAME = "FAKE_SERVICE"

VERSION = "1.0"


def create_args():
    return type('', (), {'producer_topic': ('%s' % OUT_TOPIC), 'consumer_topic': 'IN_TOPIC',
                         'bootstrap_servers': ['kafka1:9092', 'kafka2:9092'], 'consumer_group_id': 'GROUP_ID'})()


ARGS = create_args()


@dataclass
class FakeBenchmarkPayload(BenchmarkPayload):
    foo: str
    bar: int


FAKE_TOML = BenchmarkDoc({"var": "val"}, "var = val", "12819821982918921")

FAKE_BENCHMARK_PAYLOAD = FakeBenchmarkPayload(foo="FOO", bar=42, toml=FAKE_TOML)

BENCHMARK_EVENT = BenchmarkEvent(request_id="REQUEST_ID", message_id="MESSAGE_ID", client_id="CLIENT_ID",
                                 client_version="CLIENT_VERSION", client_user="CLIENT_USER", authenticated=False,
                                 date=42, visited=[],
                                 payload=FAKE_BENCHMARK_PAYLOAD)

VISIT_TIME = 123


class StopperKafkaServiceCallback(KafkaServiceCallback):
    def __init__(self, kafka_service: KafkaService):
        self.kafka_service = kafka_service

    def handle_event(self, event: BenchmarkEvent) -> Any:
        self.kafka_service.stop_loop()
        return None

    def cleanup(self):
        pass


# Trivial test to check if KafkaService imports something missing
def test_kafka_service_imports():
    from bai_kafka_utils.kafka_service import create_kafka_service_parser
    assert create_kafka_service_parser


MockConsumerRecord = collections.namedtuple("FakeConsumerRecord", ["key", "value"])


@fixture()
def kafka_consumer():
    consumer = MagicMock(spec=KafkaConsumer)

    consumer.poll = Mock(return_value=[
        MockConsumerRecord(value=BENCHMARK_EVENT, key="SOME_KEY")])
    return consumer


@fixture()
def kafka_producer():
    return MagicMock(spec=KafkaProducer)


@fixture()
def simple_kafka_service(kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    callbacks = []
    kafka_service = KafkaService(SERVICE_NAME, VERSION, FakeBenchmarkPayload, ARGS, callbacks, kafka_consumer,
                                 kafka_producer)
    return kafka_service


def test_kafka_service_started_twice(simple_kafka_service: KafkaService):
    simple_kafka_service._running = True
    with pytest.raises(ValueError, message=KafkaService._LOOP_IS_ALREADY_RUNNING):
        simple_kafka_service.run_loop()


def test_kafka_service_stop_before_run(simple_kafka_service: KafkaService):
    with pytest.raises(ValueError, message=KafkaService._LOOP_IS_ALREADY_RUNNING):
        simple_kafka_service.stop_loop()


def test_message_passed_through(kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback1 = Mock(spec=KafkaServiceCallback)
    mock_callback2 = Mock(spec=KafkaServiceCallback)

    mock_callbacks = [mock_callback1, mock_callback2]

    callbacks = list(mock_callbacks)

    kafka_service = KafkaService(SERVICE_NAME, VERSION, FakeBenchmarkPayload, ARGS, callbacks, kafka_consumer,
                                 kafka_producer)
    callbacks.append(StopperKafkaServiceCallback(kafka_service))

    kafka_service.run_loop()

    for callback in mock_callbacks:
        assert callback.handle_event.called
        assert callback.cleanup.called


# The patched objects are passed in the reverse order
@patch.object(time, "time_ns")
@patch.object(uuid, "uuid4")
def test_message_sent(mock_uuid4, mock_time_ns, kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback = Mock(spec=KafkaServiceCallback)

    result_event = copy.deepcopy(BENCHMARK_EVENT)
    expected_event = copy.deepcopy(result_event)

    mock_uuid4.return_value = uuid.UUID(hex=MOCK_UUID)
    mock_time_ns.return_value = VISIT_TIME

    expected_event.message_id = str(mock_uuid4())
    expected_event.visited.append(VisitedService(SERVICE_NAME, timestamp=VISIT_TIME, version=VERSION))

    mock_callback.handle_event = Mock(return_value=result_event)

    callbacks = [mock_callback]

    kafka_service = KafkaService(SERVICE_NAME, VERSION, FakeBenchmarkPayload, ARGS, callbacks, kafka_consumer,
                                 kafka_producer)
    callbacks.append(StopperKafkaServiceCallback(kafka_service))

    kafka_service.run_loop()

    kafka_producer.send.assert_called_with(OUT_TOPIC, value=expected_event)
