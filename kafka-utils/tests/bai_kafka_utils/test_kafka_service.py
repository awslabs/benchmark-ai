import collections
import copy
import re
import time
import uuid
from dataclasses import dataclass
from typing import List, Dict
from unittest.mock import MagicMock, Mock, call

import pytest
from kafka import KafkaConsumer, KafkaProducer
from pytest import fixture

from bai_kafka_utils.events import (
    BenchmarkPayload,
    BenchmarkEvent,
    BenchmarkDoc,
    VisitedService,
    StatusMessageBenchmarkEvent,
    Status,
)
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceCallback

CLIENT_ID = "CLIENT_ID"

MOCK_MD5 = "12819821982918921"

SOME_KEY = "SOME_KEY"

MOCK_UUID = "4B545FB7-66B6-4C24-A681-7F1625313257"

PRODUCER_TOPIC = "OUT_TOPIC"

SERVICE_NAME = "FAKE_SERVICE"

POD_NAME = "POD_NAME"

VERSION = "1.0"

VISIT_TIME = 123
VISIT_TIME_MS = VISIT_TIME * 1000

CONSUMER_TOPIC = "IN_TOPIC"

CMD_RETURN_TOPIC = "CMD_RETURN"
CMD_SUBMIT_TOPIC = "CMD_SUBMIT"

STATUS_TOPIC = "STATUS_TOPIC"

STATUS_MESSAGE = "MESSAGE"


@dataclass
class MockBenchmarkPayload(BenchmarkPayload):
    foo: str
    bar: int


def create_mock_consumer_record(key, value, topic):
    MockConsumerRecord = collections.namedtuple("FakeConsumerRecord", ["key", "value"])
    MockConsumerRecord.topic = topic

    return MockConsumerRecord(key=key, value=value)


@fixture
def benchmark_event():
    doc = BenchmarkDoc({"var": "val"}, "var = val", MOCK_MD5)
    payload = MockBenchmarkPayload(foo="FOO", bar=42, toml=doc)
    return BenchmarkEvent(
        action_id="ACTION_ID",
        message_id="MESSAGE_ID",
        client_id=CLIENT_ID,
        client_version="CLIENT_VERSION",
        client_username="CLIENT_USER",
        authenticated=False,
        tstamp=42,
        visited=[],
        type="BAI_APP_BFF",
        payload=payload,
    )


@fixture
def kafka_consumer(benchmark_event: BenchmarkEvent):
    consumer = MagicMock(spec=KafkaConsumer)
    mock_record = create_mock_consumer_record(value=benchmark_event, key=SOME_KEY, topic=CONSUMER_TOPIC)

    consumer.poll = Mock(return_value={CONSUMER_TOPIC: [mock_record]})
    return consumer


@fixture
def kafka_consumer_with_invalid_message(benchmark_event):
    consumer = MagicMock(spec=KafkaConsumer)

    # Add a good one to allow the stop handler to do it's job
    consumer.poll = Mock(
        return_value={
            CONSUMER_TOPIC: [
                create_mock_consumer_record(value=None, key=SOME_KEY, topic=CONSUMER_TOPIC),
                create_mock_consumer_record(value=benchmark_event, key=SOME_KEY, topic=CONSUMER_TOPIC),
            ]
        }
    )
    return consumer


@fixture
def kafka_consumer_with_two_topics(benchmark_event):
    consumer = MagicMock(spec=KafkaConsumer)

    # Add a good one to allow the stop handler to do it's job
    consumer.poll = Mock(
        return_value={
            CONSUMER_TOPIC: [create_mock_consumer_record(value=benchmark_event, key=SOME_KEY, topic=CONSUMER_TOPIC)],
            CMD_SUBMIT_TOPIC: [
                create_mock_consumer_record(value=benchmark_event, key=SOME_KEY, topic=CMD_SUBMIT_TOPIC)
            ],
        }
    )
    return consumer


@fixture
def kafka_producer():
    return MagicMock(spec=KafkaProducer)


@fixture
def simple_kafka_service(kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    callbacks = {}
    kafka_service = KafkaService(
        name=SERVICE_NAME,
        version=VERSION,
        callbacks=callbacks,
        kafka_consumer=kafka_consumer,
        kafka_producer=kafka_producer,
        pod_name=POD_NAME,
    )
    return kafka_service


def test_dont_add_to_running(simple_kafka_service: KafkaService):
    simple_kafka_service._running = True
    with pytest.raises(
        KafkaService.LoopAlreadyRunningException, match=re.escape(KafkaService._CANNOT_UPDATE_CALLBACKS)
    ):
        simple_kafka_service.add_callback(MagicMock(spec=KafkaServiceCallback), CONSUMER_TOPIC)


def test_dont_remove_from_running(simple_kafka_service: KafkaService):
    simple_kafka_service._running = True
    with pytest.raises(
        KafkaService.LoopAlreadyRunningException, match=re.escape(KafkaService._CANNOT_UPDATE_CALLBACKS)
    ):
        simple_kafka_service.remove_callback(MagicMock(spec=KafkaServiceCallback), CONSUMER_TOPIC)


def test_kafka_service_started_twice(simple_kafka_service: KafkaService):
    simple_kafka_service._running = True
    with pytest.raises(
        KafkaService.LoopAlreadyRunningException, match=re.escape(KafkaService._LOOP_IS_ALREADY_RUNNING)
    ):
        simple_kafka_service.run_loop()


def test_kafka_service_stop_before_run(simple_kafka_service: KafkaService):
    assert not simple_kafka_service.running
    with pytest.raises(KafkaService.LoopNotRunningException, match=re.escape(KafkaService._IS_NOT_RUNNING)):
        simple_kafka_service.stop_loop()


def _create_mock_callback():
    mock_callback = MagicMock(spec=KafkaServiceCallback)
    return mock_callback


def test_invalid_message_ignored(kafka_consumer_with_invalid_message: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback = _create_mock_callback()
    kafka_service = _create_kafka_service(
        {CONSUMER_TOPIC: [mock_callback]}, kafka_consumer_with_invalid_message, kafka_producer
    )
    kafka_service.run_loop()
    # Nothing done for broken message
    with pytest.raises(AssertionError):
        assert mock_callback.handle_event.assert_called_with(None, kafka_service)
    assert mock_callback.handle_event.call_count == 1


def test_not_consumed_topic_ignored(kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback = _create_mock_callback()
    kafka_service = _create_kafka_service({"ANOTHER_TOPIC": [mock_callback]}, kafka_consumer, kafka_producer)
    kafka_service.run_loop()

    assert not mock_callback.handle_event.called
    assert mock_callback.cleanup.called


def test_multiple_consumed_topics(kafka_consumer_with_two_topics: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback = _create_mock_callback()
    kafka_service = _create_kafka_service(
        {CONSUMER_TOPIC: [mock_callback], CMD_SUBMIT_TOPIC: [mock_callback]},
        kafka_consumer_with_two_topics,
        kafka_producer,
    )
    kafka_service.run_loop()

    assert mock_callback.handle_event.call_count == 2
    mock_callback.cleanup.assert_called_once()


def test_message_passed_through(kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback1 = _create_mock_callback()
    mock_callback2 = _create_mock_callback()

    mock_callbacks = [mock_callback1, mock_callback2]

    kafka_service = _create_kafka_service({CONSUMER_TOPIC: mock_callbacks}, kafka_consumer, kafka_producer)
    kafka_service.run_loop()

    for callback in mock_callbacks:
        assert callback.handle_event.called
        assert callback.cleanup.called


def test_immutable_callbacks(kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer):
    mock_callback_passed = _create_mock_callback()
    mock_callback_added_later = _create_mock_callback()

    callbacks = [mock_callback_passed]

    kafka_service = _create_kafka_service({CONSUMER_TOPIC: callbacks}, kafka_consumer, kafka_producer)

    callbacks.append(mock_callback_added_later)

    kafka_service.run_loop()

    assert mock_callback_passed.handle_event.called
    assert mock_callback_passed.cleanup.called

    assert not mock_callback_added_later.handle_event.called
    assert not mock_callback_added_later.cleanup.called


def test_message_sent(
    mocker, kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer, benchmark_event: BenchmarkEvent
):
    class SendMessageCallback(KafkaServiceCallback):
        def __init__(self, topic):
            self.topic = topic

        def handle_event(self, event: BenchmarkEvent, kafka_service: KafkaService):
            kafka_service.send_event(event, topic=self.topic)

        def cleanup(self):
            pass

    mock_time, mock_uuid4 = mock_time_and_uuid(mocker)

    result_event = copy.deepcopy(benchmark_event)
    expected_event = copy.deepcopy(result_event)

    mock_message_before_send(expected_event, mock_uuid4, PRODUCER_TOPIC)

    callback = SendMessageCallback(PRODUCER_TOPIC)

    kafka_service = _create_kafka_service({CONSUMER_TOPIC: [callback]}, kafka_consumer, kafka_producer)
    kafka_service.run_loop()

    response_call = call(PRODUCER_TOPIC, value=expected_event, key=CLIENT_ID)
    kafka_producer.send.assert_has_calls([response_call])


def mock_time_and_uuid(mocker):
    mock_time = mocker.patch.object(time, "time", return_value=VISIT_TIME)
    mock_uuid4 = mocker.patch("bai_kafka_utils.kafka_service.uuid.uuid4", return_value=uuid.UUID(hex=MOCK_UUID))
    return mock_time, mock_uuid4


# Helper to create a KafkaService to test
def _create_kafka_service(callbacks: Dict[str, List[KafkaServiceCallback]], kafka_consumer, kafka_producer):
    class StopKafkaServiceCallback(KafkaServiceCallback):
        def handle_event(self, event: BenchmarkEvent, kafka_service: KafkaService):
            kafka_service.stop_loop()
            return None

        def cleanup(self):
            pass

    kafka_service = KafkaService(
        name=SERVICE_NAME,
        version=VERSION,
        callbacks=callbacks,
        kafka_consumer=kafka_consumer,
        kafka_producer=kafka_producer,
        pod_name=POD_NAME,
        status_topic=STATUS_TOPIC,
    )
    kafka_service.add_callback(StopKafkaServiceCallback(), CONSUMER_TOPIC)
    return kafka_service


class DoNothingCallback(KafkaServiceCallback):
    def handle_event(self, event: BenchmarkEvent, kafka_service: KafkaService):
        return None

    def cleanup(self):
        pass


def test_status_message_sent(
    mocker, kafka_consumer: KafkaConsumer, kafka_producer: KafkaProducer, benchmark_event: BenchmarkEvent
):
    mock_time, mock_uuid4 = mock_time_and_uuid(mocker)

    status_callback = DoNothingCallback()

    kafka_service = _create_kafka_service({STATUS_TOPIC: [status_callback]}, kafka_consumer, kafka_producer)
    kafka_service.run_loop()

    expected_status_event = StatusMessageBenchmarkEvent.create_from_event(
        Status.PENDING, f"{SERVICE_NAME} service, node {POD_NAME}: Processing event...", benchmark_event
    )

    mock_message_before_send(expected_status_event, mock_uuid4, STATUS_TOPIC)

    kafka_producer.send.assert_called_with(STATUS_TOPIC, value=expected_status_event, key=CLIENT_ID)


def mock_message_before_send(status_event, mock_uuid4, topic):
    status_event.message_id = str(mock_uuid4())
    status_event.visited.append(VisitedService(SERVICE_NAME, tstamp=VISIT_TIME_MS, version=VERSION, node=POD_NAME))
    status_event.type = topic
