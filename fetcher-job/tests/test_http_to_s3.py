from pycurl import Curl

import pytest
from pytest import fixture
from typing import TextIO
from unittest.mock import Mock, patch, MagicMock, create_autospec

import benchmarkai_fetcher_job
from benchmarkai_fetcher_job.failures import HttpServerError, HttpClientError, InvalidDigestError
from benchmarkai_fetcher_job.http_to_s3 import http_to_s3
from benchmarkai_fetcher_job.md5sum import DigestPair
from benchmarkai_fetcher_job.s3_utils import S3Object

S3DST = S3Object("bucket", "key")

SRC = "http://myserver.com/foo.zip"

DST = "s3://bucket/key"

MD5 = "42"

WRONG_MD5 = "23"

ETAG = "42"


@fixture(autouse=True)
def mock_temp_file(mocker):
    mock_TemporaryFile = mocker.patch.object(benchmarkai_fetcher_job.http_to_s3.tempfile, "TemporaryFile")
    mock_file = create_autospec(TextIO)
    mock_TemporaryFile.return_value = mock_file

    # So the guy can be used with with
    mock_file.__enter__.return_value = mock_file
    return mock_file


@fixture
def mock_check_s3_for_md5(mocker):
    return mocker.patch.object(
        benchmarkai_fetcher_job.http_to_s3, "check_s3_for_md5", autospec=True, return_value=False
    )


@fixture
def mock_check_s3_for_etag(mocker):
    return mocker.patch.object(
        benchmarkai_fetcher_job.http_to_s3, "check_s3_for_etag", autospec=True, return_value=False
    )


@fixture
def mock_upload_to_s3(mocker):
    return mocker.patch.object(benchmarkai_fetcher_job.http_to_s3, "upload_to_s3", autospec=True)


@fixture
def mock_update_s3_hash_tagging(mocker):
    return mocker.patch.object(benchmarkai_fetcher_job.http_to_s3, "update_s3_hash_tagging", autospec=True)


@fixture
def mock_calculate_md5_and_etag(mocker):
    return mocker.patch.object(
        benchmarkai_fetcher_job.http_to_s3, "calculate_md5_and_etag", autospec=True, return_value=DigestPair(MD5, ETAG)
    )


@fixture
def mock_successful_download(mocker):
    return mocker.patch.object(benchmarkai_fetcher_job.http_to_s3, "http_download", autospec=True)


@fixture
def mock_client_error_download(mocker):
    return mocker.patch.object(
        benchmarkai_fetcher_job.http_to_s3, "http_download", autospec=True, side_effect=HttpClientError()
    )


@fixture
def mock_server_error_download(mocker):
    return mocker.patch.object(
        benchmarkai_fetcher_job.http_to_s3, "http_download", autospec=True, side_effect=HttpServerError()
    )


def test_success(
    mock_calculate_md5_and_etag,
    mock_update_s3_hash_tagging,
    mock_upload_to_s3,
    mock_check_s3_for_md5,
    mock_check_s3_for_etag,
    mock_temp_file,
    mock_successful_download,
):
    http_to_s3(SRC, DST)

    mock_check_s3_for_md5.assert_not_called()
    mock_upload_to_s3.assert_called_with(mock_temp_file, S3DST)
    mock_calculate_md5_and_etag.assert_called_with(mock_temp_file)
    mock_update_s3_hash_tagging.assert_called_with(S3DST, MD5)


def test_success_with_md5(
    mock_calculate_md5_and_etag,
    mock_update_s3_hash_tagging,
    mock_upload_to_s3,
    mock_check_s3_for_md5,
    mock_check_s3_for_etag,
    mock_temp_file,
    mock_successful_download,
):
    http_to_s3(SRC, DST, MD5)

    mock_check_s3_for_md5.assert_called_with(S3DST, MD5)
    mock_upload_to_s3.assert_called_with(mock_temp_file, S3DST)
    mock_calculate_md5_and_etag.assert_called_with(mock_temp_file)
    mock_update_s3_hash_tagging.assert_called_with(S3DST, MD5)


def test_success_with_wrong_md5(
    mock_calculate_md5_and_etag,
    mock_update_s3_hash_tagging,
    mock_upload_to_s3,
    mock_check_s3_for_md5,
    mock_check_s3_for_etag,
    mock_temp_file,
    mock_successful_download,
):
    with pytest.raises(InvalidDigestError):
        http_to_s3(SRC, DST, WRONG_MD5)

    mock_upload_to_s3.assert_not_called()
    mock_update_s3_hash_tagging.assert_not_called()


def test_success_with_md5_cache_hit(
    mock_calculate_md5_and_etag,
    mock_update_s3_hash_tagging,
    mock_upload_to_s3,
    mock_check_s3_for_md5,
    mock_check_s3_for_etag,
    mock_temp_file,
    mock_successful_download,
):
    mock_check_s3_for_md5.return_value = True

    http_to_s3(SRC, DST, MD5)

    mock_check_s3_for_md5.assert_called_with(S3DST, MD5)

    mock_successful_download.assert_not_called()


def test_success_with_etag_cache_hit(
    mock_calculate_md5_and_etag,
    mock_update_s3_hash_tagging,
    mock_upload_to_s3,
    mock_check_s3_for_md5,
    mock_check_s3_for_etag,
    mock_temp_file,
    mock_successful_download,
):
    mock_check_s3_for_etag.return_value = True

    http_to_s3(SRC, DST, MD5)

    mock_successful_download.assert_called_once()
    mock_upload_to_s3.assert_not_called()
    mock_update_s3_hash_tagging.assert_called_with(S3DST, MD5)


def test_server_error(mock_server_error_download):
    with pytest.raises(HttpServerError):
        http_to_s3(SRC, DST)


def test_client_error(mock_client_error_download):
    with pytest.raises(HttpClientError):
        http_to_s3(SRC, DST)
