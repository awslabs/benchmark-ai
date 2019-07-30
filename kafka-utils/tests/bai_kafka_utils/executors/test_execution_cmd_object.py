from unittest.mock import create_autospec

from bai_kafka_utils.executors.execution_callback import ExecutionEngine
from bai_kafka_utils.executors.execution_cmd_object import ExecutorCommandObject

ACTION_ID = "ACTION_ID"

CLIENT_ID = "CLIENT_ID"


def test_distinct_engines():
    mock_engine: ExecutionEngine = create_autospec(ExecutionEngine)
    engines = {"FOO": mock_engine, "BAR": mock_engine}

    cmd_object = ExecutorCommandObject(engines)
    cmd_object.cancel(CLIENT_ID, ACTION_ID)

    mock_engine.cancel.assert_called_once_with(CLIENT_ID, ACTION_ID)
