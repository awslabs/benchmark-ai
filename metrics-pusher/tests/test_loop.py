from contextlib import contextmanager
from unittest import mock

import datetime
import pytest
import time
from threading import Thread
from unittest.mock import MagicMock, call

from bai_metrics_pusher.args import InputValue
from bai_metrics_pusher.loop import listen_to_fifos_and_emit_metrics, start_loop, generate_lines_from_fifos


@contextmanager
def create_mock_for_generate_lines_from_fifos(lines):
    with mock.patch(
        "bai_metrics_pusher.loop.generate_lines_from_fifos", autospec=True
    ) as mock_generate_lines_from_fifos:
        mock_generate_lines_from_fifos.return_value = lines
        yield
        # yield from lines


@pytest.fixture(autouse=True)
def mock_start_kubernetes_pod_watcher(mocker):
    yield mocker.patch("bai_metrics_pusher.loop.start_kubernetes_pod_watcher")


def test_listen_to_fifo_and_emit_metrics():
    backend = MagicMock()

    with create_mock_for_generate_lines_from_fifos(['{"metric1": 1}\n', '{"metric2": 2}\n']):
        listen_to_fifos_and_emit_metrics(["/tmp/benchmarkai/fifo"], backend)
    assert backend.emit.call_args_list == [call({"metric1": 1}), call({"metric2": 2})]


def test_start_loop(mock_start_kubernetes_pod_watcher):
    metrics_pusher_input = InputValue(
        backend="stdout", pod_name="pod-name", pod_namespace="pod-namespace", backend_args={}
    )
    with create_mock_for_generate_lines_from_fifos('{"metric1": 1}\n{"metric2": 2}\n'):
        start_loop(metrics_pusher_input)

    assert mock_start_kubernetes_pod_watcher.call_count == 1


def test_generate_lines_from_fifo(tmp_path, request):
    temp_directory = tmp_path / "bai-fifos"
    temp_directory.mkdir()
    fifo1 = temp_directory / "fifo1"
    fifo2 = temp_directory / "fifo2"
    request.addfinalizer(fifo1.unlink)
    request.addfinalizer(fifo2.unlink)

    def write_to_fifos():
        # Wait until all fifos are created
        deadline = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
        while deadline > datetime.datetime.utcnow():
            if fifo1.exists() and fifo2.exists():
                break
            time.sleep(0.01)

        # Now write some lines to each FIFO
        with open(str(fifo1), "w") as f:
            f.write("Fifo1-line1\n")
            f.write("Fifo1-line2\n")
        with open(str(fifo2), "w") as f:
            f.write("Fifo2-line1\n")
            f.write("Fifo2-line2\n")

    # Write to the FIFO files in another because we're simulating as if a benchmark would be running, which is always
    # in another process
    thread = Thread(target=write_to_fifos)
    thread.start()
    lines = list(generate_lines_from_fifos([str(fifo1), str(fifo2)]))
    assert not thread.is_alive()
    assert sorted(lines) == ["Fifo1-line1\n", "Fifo1-line2\n", "Fifo2-line1\n", "Fifo2-line2\n"]
