import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import boto3


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


def upload_to_s3(fp, dst: S3Object):
    logger = logging.getLogger(__name__)

    logger.info(f"Start upload to {dst}")
    boto3.client("s3").upload_fileobj(fp, dst.bucket, dst.key)
    logger.info(f"End upload to {dst}")
