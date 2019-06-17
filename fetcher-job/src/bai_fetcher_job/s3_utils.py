import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from typing import TextIO

from bai_fetcher_job.failures import S3Error

MD5_TAG = "MD5"

logger = logging.getLogger(__name__)


@dataclass
class S3Object:
    bucket: str
    key: str

    @classmethod
    def parse(cls, url: str):
        dst_url = urlparse(url)

        bucket = dst_url.netloc
        key = dst_url.path[1:]

        return S3Object(bucket=bucket, key=key)

    def __str__(self):
        return f"s3://{self.bucket}/{self.key}"


def upload_to_s3(fp, dst: S3Object):
    fp.seek(0)
    logger.info(f"Start upload to {dst}")
    try:
        boto3.client("s3").upload_fileobj(fp, dst.bucket, dst.key, Callback=ProgressCallback())
    except ClientError as e:
        raise S3Error from e
    logger.info(f"End upload to {dst}")


def update_s3_hash_tagging(dst: S3Object, md5: str):
    logger.info(f"Updating hash for {dst}")
    try:
        boto3.client("s3").put_object_tagging(
            Bucket=dst.bucket, Key=dst.key, Tagging={"TagSet": [{"Key": MD5_TAG, "Value": md5}]}
        )
    except ClientError as e:
        raise S3Error from e
    logger.info(f"Updated hash for {dst}")


def check_s3_for_md5(dst: S3Object, md5: str) -> bool:
    try:
        tags = boto3.client("s3").get_object_tagging(Bucket=dst.bucket, Key=dst.key)
        md5s = [tag["Value"] for tag in tags["TagSet"] if tag["Key"] == "MD5"]
        if md5s:
            return md5 == md5s[0]
    except ClientError:
        # Like no object or something
        logger.exception(f"Failed to validate hash for {dst}")
        return False
    # Ok, The file IS there. But it has no MD5 tags.
    # May be it's small enough for md5 to be the Tag?
    return check_s3_for_etag(dst, md5)


def check_s3_for_etag(dst: S3Object, etag: str) -> bool:
    try:
        boto3.client("s3").get_object(Bucket=dst.bucket, Key=dst.key, IfMatch=etag)
    except ClientError:
        # Like no object or something
        logger.exception(f"Failed to validate etag for {dst}")
        return False

    return True


class ProgressCallback:
    def __init__(self):
        self.transferred_total = 0

    def __call__(self, transferred):
        self.transferred_total += transferred
        logger.info(f"{self.transferred_total} bytes transferred")


def download_from_s3(fp: TextIO, src: str):
    s3src = S3Object.parse(src)
    logger.info(f"Start download from {src}")
    try:
        boto3.client("s3").download_fileobj(s3src.bucket, s3src.key, fp, Callback=ProgressCallback())
    except ClientError as e:
        raise S3Error from e
    logger.info(f"End download from {src}")


def is_s3_file(obj: S3Object):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(obj.bucket)

    # Are we able to access the key on it's own?
    obj = bucket.Object(obj.key)
    try:
        if obj.content_length > 0:
            return True
    except ClientError:
        logger.info(f"Failed to get content_length for {obj}. May be not an object at all")

    try:
        any_object = False
        for sub_obj in bucket.objects.filter(Prefix=obj.key):
            any_object = True
            if sub_obj.key != obj.key:
                return False
        if not any_object:
            raise S3Error("Object not found")
        # Just an empty file
        return True
    except ClientError as e:
        raise S3Error from e
