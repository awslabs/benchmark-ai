import os

import boto3
from pytest import fixture

from bai_kafka_utils.events import DataSetSizeInfo
from preflight.s3_estimator import s3_estimate_size

SINGLE_FILE_KEY = "single-file"

FOLDER_KEY = "folder"

USER_BUCKET = "user-bucket"

S3_SINGLE_FILE = f"s3://{USER_BUCKET}/{SINGLE_FILE_KEY}"

# User bucket is an "example" user bucker defined in benchmark-ai/mock-infra/s3
S3_FOLDER = f"s3://{USER_BUCKET}/{FOLDER_KEY}"

FILE_COUNT = 2
FILE_CONTENT = b"FILE"
FILE_SIZE = len(FILE_CONTENT)


@fixture
def s3():
    s3_endpoint_url = os.environ.get("S3_ENDPOINT")
    return boto3.resource("s3", endpoint_url=s3_endpoint_url)


@fixture
def s3_with_a_file(s3):
    bucket = s3.Bucket(USER_BUCKET)
    bucket.put_object(Body=FILE_CONTENT, Key=SINGLE_FILE_KEY)
    return s3


@fixture
def s3_with_a_folder(s3):
    bucket = s3.Bucket(USER_BUCKET)
    for inx in range(0, FILE_COUNT):
        bucket.put_object(Body=FILE_CONTENT, Key=f"{FOLDER_KEY}/file{inx}")
    return s3


def test_s3_with_a_file(s3_with_a_file):
    assert DataSetSizeInfo(FILE_SIZE, 1, FILE_SIZE) == s3_estimate_size(S3_SINGLE_FILE, s3_with_a_file)


def test_s3_with_a_folder(s3_with_a_folder):
    assert DataSetSizeInfo(FILE_SIZE * FILE_COUNT, FILE_COUNT, FILE_SIZE) == s3_estimate_size(
        S3_FOLDER, s3_with_a_folder
    )
