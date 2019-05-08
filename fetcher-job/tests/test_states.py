import pytest

from benchmarkai_fetcher_job.states import FetcherResult, FetcherStatus

FETCHER_DONE_RESULT = FetcherResult(FetcherStatus.DONE, "Success")

STATE_DONE_BIN = b'{"status": "DONE", "message": "Success"}'

STATE_RUNNING_BIN = b'{"status": "RUNNING"}'

STATE_STRANGE_BIN = b'{"status": "STRANGE"}'


def test_serialize_state():
    assert STATE_DONE_BIN == FETCHER_DONE_RESULT.to_binary()


def test_deserialize_state():
    assert FetcherResult.from_binary(STATE_DONE_BIN) == FETCHER_DONE_RESULT


def test_deserialize_state_final():
    result = FetcherResult.from_binary(STATE_DONE_BIN)
    assert result.status.final


def test_deserialize_state_not_final():
    result = FetcherResult.from_binary(STATE_RUNNING_BIN)
    assert not result.status.final


def test_deserialize_state_strange():
    with pytest.raises(Exception):
        FetcherResult.from_binary(STATE_STRANGE_BIN)


def test_finals():
    assert not FetcherStatus.PENDING.final
    assert not FetcherStatus.RUNNING.final

    assert FetcherStatus.DONE.final
    assert FetcherStatus.FAILED.final
