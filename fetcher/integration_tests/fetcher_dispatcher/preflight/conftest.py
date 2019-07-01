import os

import boto3
from pytest import fixture


@fixture
def s3():
    s3_endpoint_url = os.environ.get("S3_ENDPOINT")
    print(f"S3 endpoint = {s3_endpoint_url}")
    print(os.environ)
    return boto3.resource("s3", endpoint_url=s3_endpoint_url)


@fixture
def s3_with_a_file(s3):
    bucket = s3.Bucket("user-bucket")
    bucket.put_object(Body=b"FILE", Key="single-file")
    return s3


@fixture
def s3_with_a_folder(s3):
    bucket = s3.Bucket("user-bucket")
    bucket.put_object(Body=b"FILE", Key="folder/file1")
    bucket.put_object(Body=b"FILE", Key="folder/file2")
    return s3
