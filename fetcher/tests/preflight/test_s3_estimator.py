import boto3
from botocore.stub import Stubber
from pytest import fixture
from typing import NamedTuple, Any, List

from bai_kafka_utils.events import DataSetSizeInfo
from preflight.s3_estimator import s3_estimate_size

BUCKET = "some_data"

SOME_SIZE = 123
FOLDER_KEY = "folder"
FILE_KEY = f"{FOLDER_KEY}/file"

SOME_S3_FILE = f"s3://{BUCKET}/{FILE_KEY}"

SOME_S3_FOLDER = f"s3://{BUCKET}/{FOLDER_KEY}"

StubedS3 = NamedTuple("x", fields=[("s3", Any), ("stub", Stubber)])
S3Obj = NamedTuple("x", fields=[("key", str), ("size", int)])


def mock_file_size(stub: Stubber, key: str, size: int):
    file_response = {"ContentLength": size}
    file_params = {"Bucket": BUCKET, "Key": key}
    stub.add_response("head_object", file_response, file_params)


def mock_list_objects(stub: Stubber, key: str, files: List[S3Obj]):
    list_params = {"Bucket": BUCKET, "Prefix": key}
    list_response = {"Contents": [{"Key": f.key, "Size": f.size} for f in files]}
    stub.add_response("list_objects", list_response, list_params)


@fixture
def mock_s3():
    s3 = boto3.resource("s3")
    stub = Stubber(s3.meta.client)
    return StubedS3(s3, stub)


@fixture
def mock_s3_with_file(mock_s3: StubedS3):
    mock_file_size(mock_s3.stub, FILE_KEY, SOME_SIZE)

    mock_s3.stub.activate()
    return mock_s3.s3


@fixture
def mock_s3_with_folder(mock_s3: StubedS3):
    mock_file_size(mock_s3.stub, FOLDER_KEY, 0)
    mock_list_objects(mock_s3.stub, FOLDER_KEY, [S3Obj(FILE_KEY, SOME_SIZE)])
    mock_file_size(mock_s3.stub, FILE_KEY, SOME_SIZE)

    mock_s3.stub.activate()
    return mock_s3.s3


def test_s3_estimator_file(mock_s3_with_file):
    size_info = s3_estimate_size(SOME_S3_FILE, mock_s3_with_file)
    assert size_info == DataSetSizeInfo(SOME_SIZE, 1, SOME_SIZE)


def test_s3_estimator_folder(mock_s3_with_folder):
    size_info = s3_estimate_size(SOME_S3_FOLDER, mock_s3_with_folder)
    assert size_info == DataSetSizeInfo(SOME_SIZE, 1, SOME_SIZE)
