import os

import boto3
from pytest import fixture

from preflight.data_set_size import DataSetSizeInfo
from preflight.s3_estimator import s3_estimate_size

S3_SINGLE_FILE = "s3://user-bucket/single-file"

S3_FOLDER = "s3://user-bucket/folder"

FILE_COUNT = 2
FILE_CONTENT = b"FILE"
FILE_SIZE = len(FILE_CONTENT)


@fixture
def s3():
    s3_endpoint_url = os.environ.get("S3_ENDPOINT")
    return boto3.resource("s3", endpoint_url=s3_endpoint_url)


@fixture
def s3_with_a_file(s3):
    bucket = s3.Bucket("user-bucket")
    bucket.put_object(Body=FILE_CONTENT, Key="single-file")
    return s3


@fixture
def s3_with_a_folder(s3):
    bucket = s3.Bucket("user-bucket")
    for inx in range(0, FILE_COUNT):
        bucket.put_object(Body=FILE_CONTENT, Key=f"folder/file{inx}")
    return s3


def test_s3_with_a_file(s3_with_a_file):
    assert DataSetSizeInfo(FILE_SIZE, 1, FILE_SIZE) == s3_estimate_size(S3_SINGLE_FILE, s3_with_a_file)


def test_s3_with_a_folder(s3_with_a_folder):
    assert DataSetSizeInfo(FILE_SIZE * FILE_COUNT, FILE_COUNT, FILE_SIZE) == s3_estimate_size(
        S3_FOLDER, s3_with_a_folder
    )
