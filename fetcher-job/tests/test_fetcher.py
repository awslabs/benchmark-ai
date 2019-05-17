import pytest
from bai_zk_utils.states import FetcherStatus, FetcherResult
from pytest import fixture

from benchmarkai_fetcher_job import fetcher
from benchmarkai_fetcher_job.args import FetcherJobConfig, RetryConfig
from benchmarkai_fetcher_job.failures import HttpClientError, HttpServerError
from benchmarkai_fetcher_job.fetcher import SUCCESS_MESSAGE, retrying_fetch


SERVER_ERROR = "I'm sick"

FILE_NOT_FOUND = "File not found"

HTTP_SRC = "http://something.com/dataset.zip"

S3_SRC = "s3://bucket/src"

DST = "s3://bucket/mykey"

ZK_NODE_PATH = "/zk/node"

ZK_ENSEMBLE = "Z1"


@fixture
def mock_http_to_s3(mocker):
    return mocker.patch.object(fetcher, "http_to_s3")


@fixture
def mock_s3_to_s3(mocker):
    return mocker.patch.object(fetcher, "s3_to_s3")


@fixture
def mock_http_to_s3_client_error(mock_http_to_s3):
    mock_http_to_s3.side_effect = HttpClientError(FILE_NOT_FOUND)
    return mock_http_to_s3


@fixture
# Fail 2 times, then succeed
def mock_http_to_s3_server_error(mock_http_to_s3):
    mock_http_to_s3.side_effect = [HttpServerError(SERVER_ERROR), HttpServerError(SERVER_ERROR), None]
    return mock_http_to_s3


@fixture
def mock_update_zk_node(mocker):
    return mocker.patch.object(fetcher, "update_zk_node")


def test_fetcher_http_to_s3(mock_http_to_s3, mock_s3_to_s3):
    cfg = FetcherJobConfig(HTTP_SRC, DST)

    retrying_fetch(cfg)

    mock_http_to_s3.assert_called_once()
    mock_s3_to_s3.assert_not_called()


def test_fetcher_s3_to_s3(mock_http_to_s3, mock_s3_to_s3):
    cfg = FetcherJobConfig(S3_SRC, DST)

    retrying_fetch(cfg)

    mock_http_to_s3.assert_not_called()
    mock_s3_to_s3.assert_called_once()


def test_fetcher_updates_zk(mock_http_to_s3, mock_update_zk_node):
    cfg = FetcherJobConfig(HTTP_SRC, DST, zk_node_path=ZK_NODE_PATH, zookeeper_ensemble_hosts=ZK_ENSEMBLE)

    retrying_fetch(cfg)

    mock_update_zk_node.assert_called_with(
        ZK_NODE_PATH, ZK_ENSEMBLE, FetcherResult(FetcherStatus.DONE, SUCCESS_MESSAGE)
    )


def test_fetcher_updates_zk_fail(mock_http_to_s3_client_error, mock_update_zk_node):
    cfg = FetcherJobConfig(HTTP_SRC, DST, zk_node_path=ZK_NODE_PATH, zookeeper_ensemble_hosts=ZK_ENSEMBLE)

    retrying_fetch(cfg)

    mock_update_zk_node.assert_called_with(
        ZK_NODE_PATH, ZK_ENSEMBLE, FetcherResult(FetcherStatus.FAILED, FILE_NOT_FOUND)
    )


def test_fetcher_updates_zk_once(mock_http_to_s3_server_error, mock_update_zk_node):
    cfg = FetcherJobConfig(
        HTTP_SRC,
        DST,
        zk_node_path=ZK_NODE_PATH,
        zookeeper_ensemble_hosts=ZK_ENSEMBLE,
        retry=RetryConfig(max_attempts=1),
    )

    retrying_fetch(cfg)

    mock_update_zk_node.assert_called_with(ZK_NODE_PATH, ZK_ENSEMBLE, FetcherResult(FetcherStatus.FAILED, SERVER_ERROR))


def test_fetcher_updates_zk_retried(mock_http_to_s3_server_error, mock_update_zk_node):
    cfg = FetcherJobConfig(
        HTTP_SRC,
        DST,
        zk_node_path=ZK_NODE_PATH,
        zookeeper_ensemble_hosts=ZK_ENSEMBLE,
        retry=RetryConfig(max_attempts=3),
    )

    retrying_fetch(cfg)

    mock_update_zk_node.assert_called_with(
        ZK_NODE_PATH, ZK_ENSEMBLE, FetcherResult(FetcherStatus.DONE, SUCCESS_MESSAGE)
    )


def test_fetcher_http_runtime_error(mock_http_to_s3):
    cfg = FetcherJobConfig(HTTP_SRC, DST)

    mock_http_to_s3.side_effect = ValueError("Something bad")

    with pytest.raises(ValueError):
        retrying_fetch(cfg)
