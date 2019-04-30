import collections
import copy
import re
import time
import uuid
from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from kafka import KafkaConsumer, KafkaProducer
from pytest import fixture

from bai_kafka_utils.events import BenchmarkPayload, BenchmarkEvent, BenchmarkDoc, VisitedService
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceCallback

MOCK_MD5 = "12819821982918921"

SOME_KEY = "SOME_KEY"

MOCK_UUID = "4B545FB7-66B6-4C24-A681-7F1625313257"

PRODUCER_TOPIC = 'OUT_TOPIC'

SERVICE_NAME = "FAKE_SERVICE"

VERSION = "1.0"

VISIT_TIME = 123
VISIT_TIME_MS = VISIT_TIME * 1000

CONSUMER_TOPIC = 'IN_TOPIC'


@dataclass
class MockBenchmarkPayload(BenchmarkPayload):
    foo: str
    bar: int


MockConsumerRecord = collections.namedtuple("FakeConsumerRecord", ["key", "value"])


@fixture
def benchmark_event():
    doc = BenchmarkDoc({"var": "val"}, "var = val", MOCK_MD5)
    payload = MockBenchmarkPayload(foo="FOO", bar=42, toml=doc)
    return BenchmarkEvent(request_id="REQUEST_ID", message_id="MESSAGE_ID", client_id="CLIENT_ID",
                          client_version="CLIENT_VERSION", client_user="CLIENT_USER", authenticated=False,
                          date=42, visited=[],
                          payload=payload)


@fixture
def kafka_consumer(benchmark_event: BenchmarkEvent):
    consumer = MagicMock(spec=KafkaConsumer)

    consumer.poll = Mock(return_value={CONSUMER_TOPIC: [
        MockConsumerRecord(value=benchmark_event, key=SOME_KEY)]})
    return consumer


@fixture
def kafka_consumer_with_invalid_message():
    consumer = MagicMock(spec=KafkaConsumer)

    # Add a good one to allow the stop handler to do it's job
    consumer.poll = Mock(return_value={CONSUMER_TOPIC: [MockConsumerRecord(value=None, key=SOME_KEY),
                                                        MockConsumerRecord(value=benchmark_event, key=SOME_KEY)]})
    return consumer


@fixture
def kafka_producer():
    return MagicMock(spec=KafkaProducer)


@fixture
def simple_kafka_service(kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    callbacks = []
    kafka_service = KafkaService(SERVICE_NAME, VERSION, PRODUCER_TOPIC, callbacks, kafka_consumer,
                                 kafka_producer)
    return kafka_service


def test_dont_add_to_running(simple_kafka_service: KafkaService):
    simple_kafka_service._running = True
    with pytest.raises(KafkaService.LoopAlreadyRunningException,
                       match=re.escape(KafkaService._CANNOT_UPDATE_CALLBACKS)):
        simple_kafka_service.add_callback(MagicMock(spec=KafkaServiceCallback))


def test_dont_remove_from_running(simple_kafka_service: KafkaService):
    simple_kafka_service._running = True
    with pytest.raises(KafkaService.LoopAlreadyRunningException,
                       match=re.escape(KafkaService._CANNOT_UPDATE_CALLBACKS)):
        simple_kafka_service.remove_callback(MagicMock(spec=KafkaServiceCallback))


def test_kafka_service_started_twice(simple_kafka_service: KafkaService):
    simple_kafka_service._running = True
    with pytest.raises(KafkaService.LoopAlreadyRunningException,
                       match=re.escape(KafkaService._LOOP_IS_ALREADY_RUNNING)):
        simple_kafka_service.run_loop()


def test_kafka_service_stop_before_run(simple_kafka_service: KafkaService):
    assert not simple_kafka_service.running
    with pytest.raises(KafkaService.LoopNotRunningException, match=re.escape(KafkaService._IS_NOT_RUNNING)):
        simple_kafka_service.stop_loop()


def test_invalid_message_ignored(kafka_consumer_with_invalid_message: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback = Mock(spec=KafkaServiceCallback)

    kafka_service = _create_kafka_service([mock_callback],
                                          kafka_consumer_with_invalid_message, kafka_producer)
    kafka_service.run_loop()

    # Nothing done for broken message
    with pytest.raises(AssertionError):
        assert mock_callback.handle_event.assert_called_with(None, kafka_service)
    assert mock_callback.handle_event.call_count == 1


def test_message_passed_through(kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback1 = Mock(spec=KafkaServiceCallback)
    mock_callback2 = Mock(spec=KafkaServiceCallback)

    mock_callbacks = [mock_callback1, mock_callback2]

    kafka_service = _create_kafka_service(mock_callbacks, kafka_consumer, kafka_producer)
    kafka_service.run_loop()

    for callback in mock_callbacks:
        assert callback.handle_event.called
        assert callback.cleanup.called


def test_immutable_callbacks(kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback_passed = Mock(spec=KafkaServiceCallback)
    mock_callback_added_later = Mock(spec=KafkaServiceCallback)

    callbacks = [mock_callback_passed]

    kafka_service = _create_kafka_service(callbacks, kafka_consumer, kafka_producer)

    callbacks.append(mock_callback_added_later)

    kafka_service.run_loop()

    assert mock_callback_passed.handle_event.called
    assert mock_callback_passed.cleanup.called

    assert not mock_callback_added_later.handle_event.called
    assert not mock_callback_added_later.cleanup.called


# The patched objects are passed in the reverse order
@patch.object(time, "time")
@patch.object(uuid, "uuid4")
def test_message_sent(mock_uuid4, mock_time, kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer,
                      benchmark_event: BenchmarkEvent):
    result_event = copy.deepcopy(benchmark_event)
    expected_event = copy.deepcopy(result_event)

    mock_uuid4.return_value = uuid.UUID(hex=MOCK_UUID)
    mock_time.return_value = VISIT_TIME

    expected_event.message_id = str(mock_uuid4())
    expected_event.visited.append(VisitedService(SERVICE_NAME, timestamp=VISIT_TIME_MS, version=VERSION))

    mock_callback = Mock(spec=KafkaServiceCallback)
    mock_callback.handle_event = Mock(return_value=result_event)

    kafka_service = _create_kafka_service([mock_callback], kafka_consumer, kafka_producer)
    kafka_service.run_loop()

    kafka_producer.send.assert_called_with(PRODUCER_TOPIC, value=expected_event)


# Helper to create a KafkaService to test
def _create_kafka_service(callbacks, kafka_consumer, kafka_producer):
    class StopKafkaServiceCallback(KafkaServiceCallback):
        def handle_event(self, event: BenchmarkEvent, kafka_service: KafkaService) -> Optional[BenchmarkEvent]:
            kafka_service.stop_loop()
            return None

        def cleanup(self):
            pass

    kafka_service = KafkaService(SERVICE_NAME, VERSION, PRODUCER_TOPIC, callbacks, kafka_consumer,
                                 kafka_producer)
    kafka_service.add_callback(StopKafkaServiceCallback())
    return kafka_service
