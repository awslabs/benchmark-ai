import logging
from dataclasses import dataclass
from typing import TextIO
from urllib.parse import urlparse

import boto3
import botocore

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
    boto3.client("s3").upload_fileobj(fp, dst.bucket, dst.key, Callback=ProgressCallback())
    logger.info(f"End upload to {dst}")


def update_s3_hash_tagging(dst: S3Object, md5: str):
    logger.info(f"Updating hash for {dst}")
    boto3.client("s3").put_object_tagging(
        Bucket=dst.bucket, Key=dst.key, Tagging={"TagSet": [{"Key": MD5_TAG, "Value": md5}]}
    )
    logger.info(f"Updated hash for {dst}")


def check_s3_for_md5(dst: S3Object, md5: str) -> bool:
    try:
        tags = boto3.client("s3").get_object_tagging(Bucket=dst.bucket, Key=dst.key)
        md5s = [tag["Value"] for tag in tags["TagSet"] if tag["Key"] == "MD5"]
        if md5s:
            return md5 == md5s[0]
    except botocore.exceptions.ClientError:
        # Like no object or something
        return False
    # Ok, The file IS there. But it has no MD5 tags.
    # May be it's small enough for md5 to be the Tag?
    return check_s3_for_etag(dst, md5)


def check_s3_for_etag(dst: S3Object, etag: str) -> bool:
    try:
        boto3.client("s3").get_object(Bucket=dst.bucket, Key=dst.key, IfMatch=etag)
    except botocore.exceptions.ClientError:
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
    boto3.client("s3").download_fileobj(s3src.bucket, s3src.key, fp, Callback=ProgressCallback())
    logger.info(f"End download from {src}")
