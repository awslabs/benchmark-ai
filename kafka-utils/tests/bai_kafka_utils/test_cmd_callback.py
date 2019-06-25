from pytest import fixture
from unittest.mock import create_autospec, Mock

from bai_kafka_utils.cmd_callback import KafkaCommandCallback
from bai_kafka_utils.events import CommandRequestEvent, CommandRequestPayload, BenchmarkEvent
from bai_kafka_utils.kafka_service import KafkaService

USER_ERROR_MESSAGE = "Something bad"

CMD_RETURN_TOPIC = "CMD_RETURN"


class CmdObject:
    def do_something(self, arg1: str, arg2: str):
        pass

    def do_with_event(self, arg1: str, arg2: str, event: BenchmarkEvent):
        pass

    def do_with_service(self, arg1: str, arg2: str, kafka_service: KafkaService):
        pass

    def do_with_client_id(self, arg: str, client_id: str):
        pass

    def do_with_action_id(self, action_id: str):
        pass

    def do_just_do(self):
        pass

    def do_throw(self):
        pass

    something_uncallable = 42

    def cleanup(self):
        pass


def get_cmd_request(cmd, args=None):
    return CommandRequestEvent(
        action_id="ACTION_ID",
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="DONTCARE",
        client_username="DONTCARE",
        authenticated=False,
        tstamp=1556814924121,
        visited=[],
        type="DONTCARE",
        payload=CommandRequestPayload(cmd, args),
    )


@fixture
def mock_result():
    return Mock()


@fixture
def mock_cmd_object(mock_result) -> CmdObject:
    mock = create_autospec(CmdObject)
    mock.do_throw.side_effect = ValueError(USER_ERROR_MESSAGE)
    mock.do_just_do.return_value = mock_result
    return mock


@fixture
def mock_kafka_service() -> KafkaService:
    return create_autospec(KafkaService)


@fixture
def callback_to_test(mock_cmd_object) -> KafkaCommandCallback:
    return KafkaCommandCallback(mock_cmd_object, CMD_RETURN_TOPIC)


def test_cmd_list(callback_to_test: KafkaCommandCallback, mock_cmd_object: CmdObject, mock_kafka_service: KafkaService):
    event = get_cmd_request("do_something", ["foo", "bar"])
    callback_to_test.handle_event(event, mock_kafka_service)
    mock_cmd_object.do_something.assert_called_once_with("foo", "bar")


def test_cmd_dict(callback_to_test: KafkaCommandCallback, mock_cmd_object: CmdObject, mock_kafka_service: KafkaService):
    event = get_cmd_request("do_something", {"arg1": "foo", "arg2": "bar"})
    callback_to_test.handle_event(event, mock_kafka_service)
    mock_cmd_object.do_something.assert_called_once_with("foo", "bar")


def test_cmd_with_event(
    callback_to_test: KafkaCommandCallback, mock_cmd_object: CmdObject, mock_kafka_service: KafkaService
):
    event = get_cmd_request("do_with_event", ["foo", "bar"])
    callback_to_test.handle_event(event, mock_kafka_service)
    mock_cmd_object.do_with_event.assert_called_once_with("foo", "bar", event=event)


def test_cmd_with_service(
    callback_to_test: KafkaCommandCallback, mock_cmd_object: CmdObject, mock_kafka_service: KafkaService
):
    event = get_cmd_request("do_with_service", ["foo", "bar"])
    callback_to_test.handle_event(event, mock_kafka_service)
    mock_cmd_object.do_with_service.assert_called_once_with("foo", "bar", kafka_service=mock_kafka_service)


def test_cmd_with_action_id_list(
    callback_to_test: KafkaCommandCallback, mock_cmd_object: CmdObject, mock_kafka_service: KafkaService
):
    event = get_cmd_request("do_with_action_id", ["foo"])
    callback_to_test.handle_event(event, mock_kafka_service)
    mock_cmd_object.do_with_action_id.assert_called_once_with(action_id="foo")


def test_cmd_with_action_id_dict(
    callback_to_test: KafkaCommandCallback, mock_cmd_object: CmdObject, mock_kafka_service: KafkaService
):
    event = get_cmd_request("do_with_action_id", {"action_id": "foo"})
    callback_to_test.handle_event(event, mock_kafka_service)
    mock_cmd_object.do_with_action_id.assert_called_once_with(action_id="foo")


def test_cmd_with_client_id(
    callback_to_test: KafkaCommandCallback, mock_cmd_object: CmdObject, mock_kafka_service: KafkaService
):
    event = get_cmd_request("do_with_client_id", ["foo"])
    callback_to_test.handle_event(event, mock_kafka_service)
    mock_cmd_object.do_with_client_id.assert_called_once_with("foo", client_id="CLIENT_ID")


def test_cmd_void(callback_to_test: KafkaCommandCallback, mock_cmd_object: CmdObject, mock_kafka_service: KafkaService):
    event = get_cmd_request("do_just_do")
    callback_to_test.handle_event(event, mock_kafka_service)
    mock_cmd_object.do_just_do.assert_called_once_with()


# Shouldn't throw
def test_cmd_unknown(callback_to_test: KafkaCommandCallback, mock_kafka_service: KafkaService):
    event = get_cmd_request("do_unknown", ["foo"])
    callback_to_test.handle_event(event, mock_kafka_service)


def test_cmd_uncallable(callback_to_test: KafkaCommandCallback, mock_kafka_service: KafkaService):
    event = get_cmd_request("something_uncallable", ["foo"])
    callback_to_test.handle_event(event, mock_kafka_service)


def test_cmd_result(callback_to_test: KafkaCommandCallback, mock_result, mock_kafka_service: KafkaService):
    event = get_cmd_request("do_just_do")
    callback_to_test.handle_event(event, mock_kafka_service)

    validate_success_result(event, mock_kafka_service, mock_result)


def test_cmd_cmd_failure(callback_to_test: KafkaCommandCallback, mock_kafka_service: KafkaService):
    event = get_cmd_request("do_throw")
    callback_to_test.handle_event(event, mock_kafka_service)

    validate_failure(event, mock_kafka_service)


def test_cmd_client_error(callback_to_test: KafkaCommandCallback, mock_kafka_service: KafkaService):
    event = get_cmd_request("do_just_do", ["illegal arg"])
    callback_to_test.handle_event(event, mock_kafka_service)

    validate_client_error(event, mock_kafka_service)


def validate_client_error(event: CommandRequestEvent, mock_kafka_service):
    event_sent = _validate_sent_event(event, mock_kafka_service)

    assert event_sent.payload.return_code == KafkaCommandCallback.CODE_CLIENT_ERROR
    assert not event_sent.payload.return_value


def validate_failure(event: CommandRequestEvent, mock_kafka_service):
    event_sent = _validate_sent_event(event, mock_kafka_service)

    assert event_sent.payload.return_code == KafkaCommandCallback.CODE_COMMAND_ERROR
    assert not event_sent.payload.return_value


def validate_success_result(event: CommandRequestEvent, mock_kafka_service, mock_result):
    event_sent = _validate_sent_event(event, mock_kafka_service)

    assert event_sent.payload.return_code == KafkaCommandCallback.CODE_SUCCESS
    assert event_sent.payload.return_value == mock_result


def _validate_sent_event(event: CommandRequestEvent, mock_kafka_service: KafkaService):
    args, kwargs = mock_kafka_service.send_event.call_args
    event_sent, topic = args
    assert topic == CMD_RETURN_TOPIC
    assert event_sent.payload.cmd_submit == event
    return event_sent


def test_pass_through_cleanup(callback_to_test: KafkaCommandCallback, mock_cmd_object: CmdObject):
    callback_to_test.cleanup()
    mock_cmd_object.cleanup.assert_called_once()


def test_no_cleanup():
    callback_to_test: KafkaCommandCallback = KafkaCommandCallback(object(), CMD_RETURN_TOPIC)
    callback_to_test.cleanup()
