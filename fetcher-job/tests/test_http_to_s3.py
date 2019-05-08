from pycurl import Curl

import pytest
from pytest import fixture
from typing import TextIO
from unittest.mock import Mock, patch, MagicMock

import benchmarkai_fetcher_job
from benchmarkai_fetcher_job.failures import HttpServerError, HttpClientError
from benchmarkai_fetcher_job.http_to_s3 import http_to_s3
from benchmarkai_fetcher_job.s3_utils import S3Object

S3DST = S3Object("bucket", "key")

SRC = "http://myserver.com/foo.zip"

DST = "s3://bucket/key"

MD5 = "42"


@fixture
def mock_curl(mocker):
    mock_Curl = mocker.patch.object(benchmarkai_fetcher_job.http_to_s3.pycurl, "Curl")
    mock_curl = Mock(spec=Curl)
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


@fixture(autouse=True)
def mock_temp_file(mocker):
    mock_TemporaryFile = mocker.patch.object(benchmarkai_fetcher_job.http_to_s3.tempfile, "TemporaryFile")
    mock_file = MagicMock(spec=TextIO)
    mock_TemporaryFile.return_value = mock_file

    # So the guy can be used with with
    mock_file.__enter__.return_value = mock_file
    return mock_file


@patch.object(benchmarkai_fetcher_job.http_to_s3, "upload_to_s3")
@patch.object(benchmarkai_fetcher_job.http_to_s3, "validate_md5")
def test_success(mock_validate_md5, mock_upload_to_s3, mock_temp_file, mock_curl_with_success):
    http_to_s3(SRC, DST)

    mock_upload_to_s3.assert_called_with(mock_temp_file, S3DST)
    mock_validate_md5.assert_not_called()

    mock_temp_file.seek.assert_called_once()


@patch.object(benchmarkai_fetcher_job.http_to_s3, "upload_to_s3")
@patch.object(benchmarkai_fetcher_job.http_to_s3, "validate_md5")
def test_success_with_md5(mock_validate_md5, mock_upload_to_s3, mock_temp_file, mock_curl_with_success):
    http_to_s3(SRC, DST, MD5)

    mock_upload_to_s3.assert_called_with(mock_temp_file, S3DST)
    mock_validate_md5.assert_called_with(mock_temp_file, MD5)
    assert mock_temp_file.seek.call_count == 2


def test_server_error(mock_curl_with_server_error):
    with pytest.raises(HttpServerError):
        http_to_s3(SRC, DST)


def test_client_error(mock_curl_with_client_error):
    with pytest.raises(HttpClientError):
        http_to_s3(SRC, DST)
