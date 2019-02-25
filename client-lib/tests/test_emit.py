from unittest import mock
import pytest

# noinspection PyProtectedMember
from benchmarkai import _emit_to_fifo, _emit_to_stdout, FifoNotCreatedInTimeError


@pytest.mark.parametrize("param", [
    [1, 2],
    "string",
    None,
    {"set"},
    1,
    1.5
])
def test_wrong_types(param):
    with pytest.raises(TypeError):
        _emit_to_stdout(param)
        _emit_to_fifo(param)


def test_empty_dictionary():
    with pytest.raises(ValueError):
        _emit_to_stdout({})
        _emit_to_fifo({})


def test_emit_to_fifo():
    import json
    metric_object = {"metric": 1}
    expected_dump = json.dumps(metric_object)
    with mock.patch("benchmarkai._getfifo") as mocked_fifo:
        _emit_to_fifo(metric_object)
    mocked_fifo.return_value.write.assert_called_once_with(expected_dump + "\n")
    mocked_fifo.return_value.flush.assert_called_once()


def test_emit_to_fifo_waits_for_file_creation_up_to_a_point():
    # import os
    # monkeypatch.setitem(os.environ, "BENCHMARK_AI_FIFO_MAX_WAIT_TIME", "1")
    # monkeypatch.setitem(os.environ, "BENCHMARK_AI_FIFO_WAIT_TIME_STEP", "0.5")

    # os.environ["BENCHMARK_AI_FIFO_MAX_WAIT_TIME"] =
    with mock.patch("io.open") as mock_open:
        with mock.patch("benchmarkai._sleep") as mock_sleep:
            with mock.patch("os.path.exists", return_value=False):
                with pytest.raises(FifoNotCreatedInTimeError):
                    _emit_to_fifo({"metric": 1})
    mock_open.assert_not_called()
    mock_sleep.assert_called()


def test_emit_to_fifo_waits_for_file_creation_then_succeed_after_file_exists():
    with mock.patch("io.open") as mock_open:
        with mock.patch("benchmarkai._sleep") as mock_sleep:
            with mock.patch("os.path.exists", side_effect=[False, True]):
                _emit_to_fifo({"metric": 1})

    mock_open.assert_called_once_with("/tmp/benchmark-ai-fifo", "w")
    mock_sleep.assert_called_once()
