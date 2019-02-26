import six
import pytest
if six.PY2:
    import mock
else:
    from unittest import mock

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
    assert mocked_fifo.return_value.flush.call_count == 1


def test_emit_to_fifo_waits_for_file_creation_up_to_a_point():
    with mock.patch("io.open") as mock_open:
        with mock.patch("benchmarkai._sleep") as mock_sleep:
            with mock.patch("os.path.exists", return_value=False):
                with pytest.raises(FifoNotCreatedInTimeError):
                    _emit_to_fifo({"metric": 1})
    mock_open.assert_not_called()
    assert mock_sleep.call_count > 0


def test_emit_to_fifo_waits_for_file_creation_then_succeed_after_file_exists():
    with mock.patch("io.open") as mock_open:
        with mock.patch("benchmarkai._sleep") as mock_sleep:
            with mock.patch("os.path.exists", side_effect=[False, True]):
                _emit_to_fifo({"metric": 1})

    mock_open.assert_called_once_with("/tmp/benchmark-ai-fifo", "w")
    assert mock_sleep.call_count == 1
