import pytest
from botocore.exceptions import ClientError
from pytest import fixture
from typing import TextIO
from unittest.mock import MagicMock, ANY

from bai_fetcher_job import s3_utils
from bai_fetcher_job.failures import S3Error
from bai_fetcher_job.s3_utils import S3Object, upload_to_s3, download_from_s3, is_s3_file

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
def mock_empty_s3_bucket(mock_s3_bucket):
    mock_s3_bucket.objects.filter.return_value = []
    return mock_s3_bucket


@fixture
def mock_s3_bucket_with_file(mock_s3_bucket):
    mock_s3_bucket.objects.filter.return_value = [S3OBJECT]
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


def test_upload_to_s3_pass_through(mock_file, mock_s3_client):
    upload_to_s3(mock_file, S3OBJECT)

    mock_file.seek.assert_called_once_with(0)
    mock_s3_client.upload_fileobj.assert_called_once_with(mock_file, S3OBJECT.bucket, S3OBJECT.key, Callback=ANY)


def test_upload_to_s3_wrap_exception(mock_file, mock_client_error_s3_client):
    with pytest.raises(S3Error):
        upload_to_s3(mock_file, S3OBJECT)


def test_download_from_s3_pass_through(mock_file, mock_s3_client):
    download_from_s3(mock_file, S3URL)
    mock_s3_client.download_fileobj.assert_called_once_with(S3OBJECT.bucket, S3OBJECT.key, mock_file, Callback=ANY)


def test_download_from_s3_wrap_exception(mock_file, mock_client_error_s3_client):
    with pytest.raises(S3Error):
        download_from_s3(mock_file, S3URL)


def test_s3_no_file(mock_empty_s3_bucket):
    with pytest.raises(S3Error):
        is_s3_file(S3OBJECT)


def test_s3_file(mock_s3_bucket_with_file):
    assert is_s3_file(S3OBJECT)


def test_s3_folder(mock_s3_bucket_with_folder):
    assert not is_s3_file(S3OBJECT)
