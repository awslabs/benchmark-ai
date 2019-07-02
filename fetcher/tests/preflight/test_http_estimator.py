import pycurl
from pycurl import Curl
from unittest.mock import call

from mock import create_autospec
from pytest import fixture

from preflight import http_estimator
from preflight.data_set_size import DataSetSizeInfo
from preflight.http_estimator import http_estimate_size

DATA_SIZE = 42

SOME_DATASET_SRC = "http://someserver.com/somedata.zip"


@fixture
def mock_curl(mocker):
    mock_Curl = mocker.patch.object(http_estimator.pycurl, "Curl")
    mock_curl = create_autospec(Curl)
    mock_Curl.return_value = mock_curl

    mock_curl.getinfo.return_value = DATA_SIZE

    return mock_curl


def test_http_estimator(mock_curl):
    size_info = http_estimate_size(SOME_DATASET_SRC)

    mock_curl.setopt.assert_has_calls(
        [call(pycurl.URL, SOME_DATASET_SRC), call(pycurl.NOBODY, 1), call(pycurl.HEADER, 1)], any_order=True
    )
    mock_curl.getinfo.assert_called_with(pycurl.CONTENT_LENGTH_DOWNLOAD)

    assert size_info == DataSetSizeInfo(DATA_SIZE, 1, DATA_SIZE)
