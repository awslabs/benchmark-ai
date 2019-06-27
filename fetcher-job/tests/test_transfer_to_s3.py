import pytest
from pytest import fixture
from typing import TextIO
from unittest.mock import create_autospec

import bai_fetcher_job
from bai_fetcher_job.failures import HttpServerError, HttpClientError, InvalidDigestError
from bai_fetcher_job.md5sum import DigestPair
from bai_fetcher_job.s3_utils import S3Object
from bai_fetcher_job.transfer_to_s3 import transfer_to_s3, DownloadCallback

S3DST = S3Object("bucket", "key")

SRC = "http://myserver.com/foo.zip"

DST = "s3://bucket/key"

MD5 = "42"

WRONG_MD5 = "23"

ETAG = "42"

TEMP_DIR = "/tmp/something"


@fixture(autouse=True)
def mock_temp_file(mocker):
    mock_file = create_autospec(TextIO)
    # So the guy can be used with with
    mock_file.__enter__.return_value = mock_file
    return mock_file


@fixture(autouse=True)
def mock_TemporaryFile(mocker, mock_temp_file):
    mock_temporaryFile = mocker.patch.object(bai_fetcher_job.transfer_to_s3.tempfile, "TemporaryFile")
    mock_temporaryFile.return_value = mock_temp_file
    return mock_temporaryFile


@fixture
def mock_check_s3_for_md5(mocker):
    # Cache miss is the default behaviour
    return mocker.patch.object(bai_fetcher_job.transfer_to_s3, "check_s3_for_md5", autospec=True, return_value=False)


@fixture
def mock_check_s3_for_etag(mocker):
    # Cache miss is the default behaviour
    return mocker.patch.object(bai_fetcher_job.transfer_to_s3, "check_s3_for_etag", autospec=True, return_value=False)


@fixture
def mock_upload_to_s3(mocker):
    return mocker.patch.object(bai_fetcher_job.transfer_to_s3, "upload_to_s3", autospec=True)


@fixture
def mock_update_s3_hash_tagging(mocker):
    return mocker.patch.object(bai_fetcher_job.transfer_to_s3, "update_s3_hash_tagging", autospec=True)


@fixture
def mock_calculate_md5_and_etag(mocker):
    return mocker.patch.object(
        bai_fetcher_job.transfer_to_s3, "calculate_md5_and_etag", autospec=True, return_value=DigestPair(MD5, ETAG)
    )


@fixture
def mock_successful_download(mocker):
    return mocker.create_autospec(DownloadCallback)


@fixture
def mock_client_error_download(mocker):
    return mocker.create_autospec(DownloadCallback, side_effect=HttpClientError())


@fixture
def mock_server_error_download(mocker):
    return mocker.create_autospec(DownloadCallback, side_effect=HttpServerError())


def test_success(
    mock_calculate_md5_and_etag,
    mock_update_s3_hash_tagging,
    mock_upload_to_s3,
    mock_check_s3_for_md5,
    mock_check_s3_for_etag,
    mock_temp_file,
    mock_successful_download,
):
    transfer_to_s3(mock_successful_download, SRC, DST)

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
    transfer_to_s3(mock_successful_download, SRC, DST, MD5)

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
        transfer_to_s3(mock_successful_download, SRC, DST, WRONG_MD5)

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

    transfer_to_s3(mock_successful_download, SRC, DST, MD5)

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

    transfer_to_s3(mock_successful_download, SRC, DST, MD5)

    mock_successful_download.assert_called_once()
    mock_upload_to_s3.assert_not_called()
    mock_update_s3_hash_tagging.assert_called_with(S3DST, MD5)


def test_server_error(mock_server_error_download):
    with pytest.raises(HttpServerError):
        transfer_to_s3(mock_server_error_download, SRC, DST)


def test_client_error(mock_client_error_download):
    with pytest.raises(HttpClientError):
        transfer_to_s3(mock_client_error_download, SRC, DST)


def test_pass_tmp_dir(
    mock_TemporaryFile,
    mock_calculate_md5_and_etag,
    mock_update_s3_hash_tagging,
    mock_upload_to_s3,
    mock_check_s3_for_md5,
    mock_check_s3_for_etag,
    mock_temp_file,
    mock_successful_download,
):
    transfer_to_s3(mock_successful_download, SRC, DST, temp_dir=TEMP_DIR)
    mock_TemporaryFile.assert_called_with("r+b", dir=TEMP_DIR)
