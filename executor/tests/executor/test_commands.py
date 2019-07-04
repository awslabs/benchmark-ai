import pytest
from bai_kafka_utils.events import create_from_object, CommandRequestEvent, CommandRequestPayload

from executor.commands import ExecutorCommandObject

KUBECTL = "kubectl"
CMD_RETURN_TOPIC = "OUT_TOPIC"
TARGET_ACTION_ID = "ACTION_ID"
CLIENT_ID = "CLIENT_ID"
WRONG_COMMAND = "WRONG_COMMAND"
RETURN_CODE_SUCCESS = 0
RETURN_VALUE = "Return value"
MESSAGE = "Message"

JOINED_RESOURCE_TYPES = ",".join(ExecutorCommandObject.ALL_K8S_RESOURCE_TYPES)


@pytest.fixture
def cancel_cmd_request_payload():
    return CommandRequestPayload(command="CANCEL", args=[TARGET_ACTION_ID])


@pytest.fixture
def cancel_cmd_request_event(benchmark_event, cancel_cmd_request_payload):
    return create_from_object(
        CommandRequestEvent, benchmark_event, payload=cancel_cmd_request_payload, client_id=CLIENT_ID
    )


@pytest.fixture
def cmd_object():
    return ExecutorCommandObject(KUBECTL)


def test_cancel_benchmark(mocker, cmd_object):
    mock_check_output = mocker.patch("executor.executor.subprocess.check_output")

    cmd_object.cancel(target_action_id=TARGET_ACTION_ID, client_id=CLIENT_ID)

    expected_call = [
        KUBECTL,
        "delete",
        JOINED_RESOURCE_TYPES,
        "--selector",
        cmd_object._create_label_selector(TARGET_ACTION_ID, CLIENT_ID),
    ]
    mock_check_output.assert_called_with(expected_call)
