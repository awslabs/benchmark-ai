#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import logging
from dataclasses import dataclass
from io import SEEK_END
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from typing import TextIO

from bai_io_utils.failures import S3Error

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
    fp.seek(0, SEEK_END)
    content_length = fp.tell()
    fp.seek(0)
    logger.info(f"Start upload to {dst}")
    try:
        boto3.client("s3").upload_fileobj(fp, dst.bucket, dst.key, Callback=ProgressCallback(content_length))
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
    def __init__(self, total_size, granularity=10):
        self.total_size = total_size
        self.transferred_total = 0
        self.granularity = granularity
        self.last_reported = 0

        self.bucket = self.total_size / self.granularity

    def __call__(self, transferred):
        if not self.total_size:
            return

        self.transferred_total += transferred
        progress = self.transferred_total / self.total_size * 100

        if self.transferred_total - self.last_reported > self.bucket:
            logger.info(f"Transferred {self.transferred_total} out of {self.total_size} ({progress:.2f}%)")
            self.last_reported = self.transferred_total


def download_from_s3(fp: TextIO, src: str):
    s3src = S3Object.parse(src)
    logger.info(f"Start download from {src}")
    try:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(s3src.bucket)
        obj = bucket.Object(s3src.key)

        obj.download_fileobj(fp, Callback=ProgressCallback(obj.content_length))
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
