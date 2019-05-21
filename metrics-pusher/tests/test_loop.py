from unittest import mock

import pytest
from unittest.mock import MagicMock, call

from contextlib import contextmanager

from bai_metrics_pusher.args import InputValue
from bai_metrics_pusher.loop import listen_to_fifo_and_emit_metrics, start_loop


@contextmanager
def create_mock_for_get_fifo_from_string(string):
    from io import StringIO

    real_stream = StringIO(string)
    mocked_stream = mock.MagicMock(wraps=real_stream)
    with mock.patch("bai_metrics_pusher.loop._get_fifo", autospec=True) as mock_get_fifo:
        mock_get_fifo.return_value.__enter__.return_value = mocked_stream
        yield mock_get_fifo


@pytest.fixture(autouse=True)
def mock_start_kubernetes_pod_watcher(mocker):
    yield mocker.patch("bai_metrics_pusher.loop.start_kubernetes_pod_watcher")


def test_listen_to_fifo_and_emit_metrics():
    backend = MagicMock()

    with create_mock_for_get_fifo_from_string('{"metric1": 1}\n{"metric2": 2}\n'):
        listen_to_fifo_and_emit_metrics(backend)
    assert backend.emit.call_args_list == [call({"metric1": 1}), call({"metric2": 2})]


def test_start_loop(mock_start_kubernetes_pod_watcher):
    metrics_pusher_input = InputValue(
        backend="stdout", pod_name="pod-name", pod_namespace="pod-namespace", backend_args={"job_id": "123"}
    )
    with create_mock_for_get_fifo_from_string('{"metric1": 1}\n{"metric2": 2}\n'):
        start_loop(metrics_pusher_input)

    assert mock_start_kubernetes_pod_watcher.call_count == 1
