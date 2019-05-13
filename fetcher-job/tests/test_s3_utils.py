import boto3
import botocore
from typing import TextIO
from unittest.mock import Mock, patch, create_autospec, MagicMock

from benchmarkai_fetcher_job import s3_utils
from benchmarkai_fetcher_job.s3_utils import S3Object, upload_to_s3

S3URL = "s3://mybucket/some_key"

S3OBJECT = S3Object("mybucket", "some_key")


def test_parse_s3_object():
    assert S3Object.parse(S3URL) == S3OBJECT


@patch.object(s3_utils, "boto3", autospec=True)
def test_upload_to_s3_pass_through(mock_boto3):
    file = create_autospec(TextIO)

    # We cannot autospec internal botocore.client.S3
    s3client = MagicMock()
    mock_boto3.client.return_value = s3client

    upload_to_s3(file, S3OBJECT)

    s3client.upload_fileobj.assert_called_with(file, S3OBJECT.bucket, S3OBJECT.key)
