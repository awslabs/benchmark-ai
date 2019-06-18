import pytest

from bai_zk_utils.states import FetcherStatus, FetcherResult, FetchedType

FETCHER_DONE_RESULT = FetcherResult(FetcherStatus.DONE, FetchedType.FILE, "Success")

STATE_DONE_BIN = b'{"status": "DONE", "type": "FILE", "message": "Success"}'

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


def test_fetch_type():
    assert str(FetchedType.FILE) == "FILE"


def test_fetch_status():
    assert str(FetcherStatus.DONE) == "DONE"
