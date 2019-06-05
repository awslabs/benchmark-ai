import pytest
from bai_kafka_utils.events import (
    create_from_object,
    CommandRequestEvent,
    CommandRequestPayload,
    CommandResponsePayload,
    CommandResponseEvent,
)

from bai_kafka_utils.kafka_service import KafkaServiceCallbackException
from executor.commands import ExecutorCommandHandler
from executor import SERVICE_NAME

KUBECTL = "kubectl"
PRODUCER_TOPIC = "OUT_TOPIC"
ACTION_ID = "ACTION_ID"
CLIENT_ID = "CLIENT_ID"
WRONG_COMMAND = "WRONG_COMMAND"
RETURN_CODE_SUCCESS = 0
RETURN_VALUE = "Return value"
MESSAGE = "Message"


@pytest.fixture
def delete_cmd_request_payload():
    return CommandRequestPayload(command="DELETE", args=[ACTION_ID])


@pytest.fixture
def delete_cmd_request_event(benchmark_event, delete_cmd_request_payload):
    return create_from_object(
        CommandRequestEvent, benchmark_event, payload=delete_cmd_request_payload, client_id=CLIENT_ID
    )


@pytest.fixture
def command_handler():
    return ExecutorCommandHandler(KUBECTL, PRODUCER_TOPIC)


def test_commands_handle_event(mocker, command_handler, delete_cmd_request_event, kafka_service):
    mock_send_response = mocker.patch("executor.commands.ExecutorCommandHandler._send_response_event")
    mock_delete_benchmark = mocker.patch("executor.commands.ExecutorCommandHandler._delete_benchmark")

    command_handler.handle_event(delete_cmd_request_event, kafka_service)

    assert mock_delete_benchmark.called_once()
    mock_delete_benchmark.assert_called_with([ACTION_ID], CLIENT_ID)
    assert mock_send_response.called_once()


def test_wrong_command(command_handler, delete_cmd_request_event, kafka_service):
    delete_cmd_request_event.payload.command = WRONG_COMMAND
    with pytest.raises(KafkaServiceCallbackException) as e:
        command_handler.handle_event(delete_cmd_request_event, kafka_service)
    assert WRONG_COMMAND in str(e)


def test_argument_missing(command_handler, delete_cmd_request_event, kafka_service):
    delete_cmd_request_event.payload.args = []
    with pytest.raises(KafkaServiceCallbackException):
        command_handler.handle_event(delete_cmd_request_event, kafka_service)


def test_delete_benchmark(mocker, command_handler, delete_cmd_request_event, kafka_service):
    mock_check_output = mocker.patch("executor.executor.subprocess.check_output")

    command_handler.handle_event(delete_cmd_request_event, kafka_service)

    expected_call = [
        KUBECTL,
        "delete",
        command_handler.ALL_K8S_RESOURCE_TYPES,
        "--selector",
        command_handler._create_label_selector(ACTION_ID, CLIENT_ID),
    ]
    assert mock_check_output.called_with(expected_call)


def test_create_label_selector(command_handler):
    label_selector = command_handler._create_label_selector(ACTION_ID, CLIENT_ID)
    expected_label_selector = (
        f"{command_handler.LABEL_ACTION_ID}={ACTION_ID},"
        f"{command_handler.LABEL_CREATED_BY}={SERVICE_NAME},"
        f"{command_handler.LABEL_CLIENT_ID}={CLIENT_ID}"
    )
    assert label_selector == expected_label_selector


def test_send_response_event(command_handler, delete_cmd_request_event, kafka_service):
    command_handler._send_response_event(
        kafka_service=kafka_service,
        input_event=delete_cmd_request_event,
        return_code=RETURN_CODE_SUCCESS,
        return_value=RETURN_VALUE,
        msg=MESSAGE,
    )

    expected_payload = CommandResponsePayload(
        return_code=RETURN_CODE_SUCCESS, return_value=RETURN_VALUE, message=MESSAGE, cmd_submit=delete_cmd_request_event
    )
    expected_response = create_from_object(CommandResponseEvent, delete_cmd_request_event, payload=expected_payload)

    kafka_service.send_event.assert_called_with(expected_response, topic=PRODUCER_TOPIC)
