import pytest

from bai_kafka_utils.events import (
    create_from_object,
    CommandRequestEvent,
    CommandRequestPayload,
)

from executor.commands import ExecutorCommandObject
from executor import SERVICE_NAME

KUBECTL = "kubectl"
CMD_RETURN_TOPIC = "OUT_TOPIC"
TARGET_ACTION_ID = "ACTION_ID"
CLIENT_ID = "CLIENT_ID"
WRONG_COMMAND = "WRONG_COMMAND"
RETURN_CODE_SUCCESS = 0
RETURN_VALUE = "Return value"
MESSAGE = "Message"


@pytest.fixture
def delete_cmd_request_payload():
    return CommandRequestPayload(command="DELETE", args=[TARGET_ACTION_ID])


@pytest.fixture
def delete_cmd_request_event(benchmark_event, delete_cmd_request_payload):
    return create_from_object(
        CommandRequestEvent, benchmark_event, payload=delete_cmd_request_payload, client_id=CLIENT_ID
    )


@pytest.fixture
def cmd_object():
    return ExecutorCommandObject(KUBECTL)


def test_delete_benchmark(mocker, cmd_object):
    mock_check_output = mocker.patch("executor.executor.subprocess.check_output")

    cmd_object.delete(target_action_id=TARGET_ACTION_ID, client_id=CLIENT_ID)

    expected_call = [
        KUBECTL,
        "delete",
        cmd_object.ALL_K8S_RESOURCE_TYPES,
        "--selector",
        cmd_object._create_label_selector(TARGET_ACTION_ID, CLIENT_ID),
    ]
    assert mock_check_output.called_with(expected_call)


def test_create_label_selector(cmd_object):
    label_selector = cmd_object._create_label_selector(TARGET_ACTION_ID, CLIENT_ID)
    expected_label_selector = (
        f"{cmd_object.LABEL_ACTION_ID}={TARGET_ACTION_ID},"
        f"{cmd_object.LABEL_CREATED_BY}={SERVICE_NAME},"
        f"{cmd_object.LABEL_CLIENT_ID}={CLIENT_ID}"
    )
    assert label_selector == expected_label_selector
