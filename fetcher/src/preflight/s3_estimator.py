import logging
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from bai_io_utils.failures import S3Error
from bai_kafka_utils.events import ContentSizeInfo

logger = logging.getLogger(__name__)


def s3_estimate_size(src: str, s3: Any = None) -> ContentSizeInfo:
    s3 = s3 or boto3.resource("s3")

    dst_url = urlparse(src)

    bucket_name = dst_url.netloc
    key = dst_url.path[1:]

    bucket = s3.Bucket(bucket_name)

    # Are we able to access the key on it's own?
    obj = bucket.Object(key)
    try:
        if obj.content_length > 0:
            return ContentSizeInfo(obj.content_length, 1, obj.content_length)
    except ClientError:
        logger.info(f"Failed to get content_length for {obj}. May be not an object at all")

    cnt = 0
    total_size = 0
    max_size = 0

    try:
        for sub_obj in bucket.objects.filter(Prefix=obj.key):
            if not sub_obj.size:
                continue

            cnt = cnt + 1
            total_size += sub_obj.size
            max_size = max(max_size, sub_obj.size)
    except ClientError as e:
        raise S3Error(str(e)) from e
    return ContentSizeInfo(int(total_size), cnt, int(max_size))
