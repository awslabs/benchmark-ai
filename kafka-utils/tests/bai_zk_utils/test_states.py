import pytest

from bai_kafka_utils.events import FetcherStatus, FetchedType
from bai_zk_utils.states import FetcherResult

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
