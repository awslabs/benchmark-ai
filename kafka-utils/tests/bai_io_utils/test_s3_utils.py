from io import SEEK_END

import pytest
from botocore.exceptions import ClientError
from pytest import fixture
from typing import TextIO
from unittest.mock import MagicMock, ANY, PropertyMock, call

from bai_io_utils import s3_utils
from bai_io_utils.failures import S3Error
from bai_io_utils.s3_utils import S3Object, upload_to_s3, download_from_s3, is_s3_file, ProgressCallback

MOCK_ERROR_RESPONSE = {"Error": {"Message": "Something is wrong"}}

S3URL = "s3://mybucket/some_key"

S3OBJECT = S3Object("mybucket", "some_key")

S3SUBOBJECT = S3Object("mybucket", "some_key/otherkey")


def test_parse_s3_object():
    assert S3Object.parse(S3URL) == S3OBJECT


@fixture
def mock_boto3(mocker):
    return mocker.patch.object(s3_utils, "boto3", autospec=True)


@fixture
def mock_s3_client(mock_boto3):

    # We cannot autospec internal botocore.client.S3
    s3client = MagicMock()
    mock_boto3.client.return_value = s3client

    return s3client


@fixture
def mock_s3_resource(mock_boto3):
    mock_s3 = MagicMock()
    mock_boto3.resource.return_value = mock_s3
    return mock_s3


@fixture
def mock_s3_bucket(mock_s3_resource):
    mock_bucket = MagicMock()
    mock_s3_resource.Bucket.return_value = mock_bucket

    return mock_bucket


@fixture
def mock_s3_object(mock_s3_bucket):
    mock_object = MagicMock()
    mock_s3_bucket.Object.return_value = mock_object
    return mock_object


@fixture
def mock_s3_file_obj(mock_s3_object):
    mock_s3_object.content_length = 42
    return mock_s3_object


@fixture
def mock_s3_failing_obj(mock_s3_object):
    type(mock_s3_object).download_fileobj = MagicMock(side_effect=ClientError(MOCK_ERROR_RESPONSE, "Download failed"))
    return mock_s3_object


@fixture
def mock_s3_folder_obj(mock_s3_object):
    type(mock_s3_object).content_length = PropertyMock(side_effect=ClientError(MOCK_ERROR_RESPONSE, "Not found"))
    return mock_s3_object


@fixture
def mock_empty_s3_bucket(mock_s3_bucket):
    mock_s3_bucket.objects.filter.return_value = []
    return mock_s3_bucket


@fixture
def mock_s3_bucket_with_file(mock_s3_bucket):
    mock_s3_bucket.objects.filter.return_value = [S3OBJECT]
    return mock_s3_bucket


@fixture
def mock_s3_bucket_with_file_no_ls(mock_s3_bucket):
    mock_s3_bucket.objects.filter.side_effect = ClientError(MOCK_ERROR_RESPONSE, "upload")
    return mock_s3_bucket


@fixture
def mock_s3_bucket_with_folder(mock_s3_bucket):
    mock_s3_bucket.objects.filter.return_value = [S3OBJECT, S3SUBOBJECT]
    return mock_s3_bucket


@fixture
def mock_client_error_s3_client(mock_s3_client):
    mock_s3_client.upload_fileobj.side_effect = ClientError(MOCK_ERROR_RESPONSE, "upload")
    mock_s3_client.download_fileobj.side_effect = ClientError(MOCK_ERROR_RESPONSE, "download")

    return mock_s3_client


@fixture
def mock_file(mocker):
    return mocker.create_autospec(TextIO)


@fixture
def mock_logger(mocker):
    return mocker.patch.object(s3_utils, "logger", autospec=True)


def test_upload_to_s3_pass_through(mock_file, mock_s3_client):
    upload_to_s3(mock_file, S3OBJECT)

    assert mock_file.seek.call_args_list == [call(0, SEEK_END), call(0)]
    mock_s3_client.upload_fileobj.assert_called_once_with(mock_file, S3OBJECT.bucket, S3OBJECT.key, Callback=ANY)


def test_upload_to_s3_wrap_exception(mock_file, mock_client_error_s3_client):
    with pytest.raises(S3Error):
        upload_to_s3(mock_file, S3OBJECT)


def test_download_from_s3_pass_through(mock_file, mock_s3_file_obj):
    download_from_s3(mock_file, S3URL)
    mock_s3_file_obj.download_fileobj.assert_called_once_with(mock_file, Callback=ANY)


def test_download_from_s3_wrap_exception(mock_file, mock_s3_failing_obj):
    with pytest.raises(S3Error):
        download_from_s3(mock_file, S3URL)


def test_s3_no_file(mock_empty_s3_bucket, mock_s3_folder_obj):
    with pytest.raises(S3Error):
        is_s3_file(S3OBJECT)


def test_s3_file(mock_s3_bucket_with_file, mock_s3_file_obj):
    assert is_s3_file(S3OBJECT)


# Special check. What if we don't have list objects permissions at all?
def test_s3_file_no_ls(mock_s3_bucket_with_file_no_ls, mock_s3_file_obj):
    assert is_s3_file(S3OBJECT)


def test_s3_folder(mock_s3_bucket_with_folder, mock_s3_folder_obj):
    assert not is_s3_file(S3OBJECT)


def test_progress(mock_logger):
    progress = ProgressCallback(total_size=100, granularity=4)
    progress(10)  # Nothing
    progress(50)  # Worth output
    progress(20)  # Nothing
    assert mock_logger.info.call_count == 1
