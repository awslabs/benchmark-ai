import pytest
from pytest import fixture

from bai_kafka_utils.events import FetcherStatus, FetchedType, DownloadableContent
from bai_zk_utils.states import FetcherResult

ERROR = "Error"

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


@fixture
def some_data_set():
    return DownloadableContent(src="http://something.com/dataset.zip", dst="s3://something/dataset.zip")


def test_update_success(some_data_set: DownloadableContent):
    FETCHER_DONE_RESULT.update(some_data_set)

    assert some_data_set.dst
    assert some_data_set.type == FetchedType.FILE
    assert not some_data_set.message


def test_update_failed(some_data_set: DownloadableContent):
    FetcherResult(FetcherStatus.FAILED, FetchedType.FILE, ERROR).update(some_data_set)

    assert not some_data_set.dst
    assert some_data_set.type == FetchedType.FILE
    assert some_data_set.message == ERROR
