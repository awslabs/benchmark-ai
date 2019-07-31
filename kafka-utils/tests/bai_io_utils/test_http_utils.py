import pycurl
from pycurl import Curl
from typing import TextIO

import pytest
from pytest import fixture
from unittest.mock import create_autospec

from bai_io_utils import http_utils
from bai_io_utils.failures import HttpServerError, HttpClientError, CurlError
from bai_io_utils.http_utils import http_download, http_perform

SRC = "http://someserver.com/somefile.zip"


@fixture
def mock_curl(mocker):
    mock_Curl = mocker.patch.object(http_utils.pycurl, "Curl")
    mock_curl = create_autospec(Curl)
    mock_Curl.return_value = mock_curl
    return mock_curl
    pass


@fixture
def mock_curl_with_success(mock_curl):
    mock_curl.getinfo.return_value = 200
    return mock_curl


@fixture
def mock_curl_with_client_error(mock_curl):
    mock_curl.getinfo.return_value = 404
    return mock_curl


@fixture
def mock_curl_with_server_error(mock_curl):
    mock_curl.getinfo.return_value = 501
    return mock_curl


@fixture
def mock_curl_not_http_error(mock_curl):
    mock_curl.perform.side_effect = pycurl.error()
    return mock_curl


@fixture
def mock_temp_file():
    return create_autospec(TextIO)


def test_http_perform_success(mock_curl_with_success):
    http_perform(mock_curl_with_success)


def test_http_perform_server_error(mock_curl_with_server_error):
    with pytest.raises(HttpServerError):
        http_perform(mock_curl_with_server_error)


def test_http_perform_client_error(mock_curl_with_client_error):
    with pytest.raises(HttpClientError):
        http_perform(mock_curl_with_client_error)


def test_http_perform_not_http_error(mock_curl_not_http_error):
    with pytest.raises(CurlError):
        http_perform(mock_curl_not_http_error)


def test_curl_passthrough(mock_temp_file, mock_curl_with_success):
    http_download(mock_temp_file, SRC)

    mock_curl_with_success.perform.assert_called_once()
    mock_curl_with_success.setopt.assert_any_call(pycurl.URL, SRC)
