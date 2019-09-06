import pytest
import copy

from unittest.mock import create_autospec, ANY

from bai_kafka_utils.executors.execution_callback import ExecutionEngine
from bai_kafka_utils.executors.execution_cmd_object import ExecutorCommandObject, Status
from bai_kafka_utils.kafka_service import KafkaService
from bai_kafka_utils.events import CommandRequestEvent

ACTION_ID = "ACTION_ID"

TARGET_ACTION_ID = "TARGET_ACTION_ID"

CLIENT_ID = "CLIENT_ID"

CASCADE = True


@pytest.fixture
def mock_kafka_service():
    return create_autospec(KafkaService)


@pytest.fixture
def command_request_event():
    return CommandRequestEvent(
        action_id=ACTION_ID,
        message_id="MESSAGE_ID",
        client_id=CLIENT_ID,
        client_version="DONTCARE",
        client_username="DONTCARE",
        authenticated=False,
        tstamp=1556814924121,
        visited=[],
        type="DONTCARE",
        payload=None,
    )


def test_distinct_engines(mock_kafka_service: KafkaService, command_request_event: CommandRequestEvent):
    mock_engine: ExecutionEngine = create_autospec(ExecutionEngine)
    engines = {"FOO": mock_engine, "BAR": mock_engine}

    cmd_object = ExecutorCommandObject(engines)
    cmd_object.cancel(mock_kafka_service, command_request_event, CLIENT_ID, TARGET_ACTION_ID, CASCADE)

    expected_handled_event = copy.deepcopy(command_request_event)

    mock_engine.cancel.assert_called_once_with(CLIENT_ID, TARGET_ACTION_ID, CASCADE)
    mock_kafka_service.send_status_message_event.assert_called_once_with(
        expected_handled_event,
        Status.SUCCEEDED,
        ANY,
        TARGET_ACTION_ID,
    )
