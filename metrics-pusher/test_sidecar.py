import os
from unittest import mock
import pytest
from contextlib import contextmanager

import benchmarkai_metrics_pusher
from benchmarkai_metrics_pusher import listen_to_fifo_and_emit_metrics


@contextmanager
def create_mock_for_get_fifo_from_string(string):
    from io import StringIO

    real_stream = StringIO(string)
    mocked_stream = mock.MagicMock(wraps=real_stream)

    # The `closed` attribute will be
    # side_effect = ([False] * string.count("\n")) + [True]
    # type(mocked_stream).closed = mock.PropertyMock(side_effect=side_effect)
    with mock.patch(
        "benchmarkai_sidecar._get_fifo", return_value=mocked_stream
    ) as mock_get_fifo:
        yield mock_get_fifo


@pytest.fixture(autouse=True)
def cleanup_fifo():
    if os.path.exists(benchmarkai_metrics_pusher.FIFO_FILEPATH):
        os.unlink(benchmarkai_metrics_pusher.FIFO_FILEPATH)


@pytest.fixture
def mock_emit():
    with mock.patch("benchmarkai_sidecar._emit") as mock_emit:
        yield mock_emit


def test_success(mock_emit):
    with create_mock_for_get_fifo_from_string('{"metric1": 1}\n{"metric2": 2}\n'):
        listen_to_fifo_and_emit_metrics()
    assert mock_emit.call_count == 2
