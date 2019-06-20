import logging

import boto3
from bai_zk_utils.states import FetchedType
from botocore.exceptions import ClientError
from typing import Optional, Dict, NamedTuple

from bai_fetcher_job.s3_utils import S3Object, download_from_s3, is_s3_file, ProgressCallback
from bai_fetcher_job.transfer_to_s3 import transfer_to_s3


# Initial version of the folder transfer, that lacks validation
# TODO Implement Merkl-tree or something like that

logger = logging.getLogger(__name__)


def _s3_to_s3_check_etag(src: Dict[str, str], src_obj, dst_obj):
    logger.info(f"Transfer {src}->{dst_obj}")

    new_obj_etag = None
    try:
        new_obj_etag = dst_obj.e_tag
    except ClientError:
        logger.info("Failed to get ETag of the destination. May be a new file")

    if src_obj.e_tag == new_obj_etag:
        logger.info("Skipping. Same ETag")
        return

    dst_obj.copy(src, Callback=ProgressCallback(src_obj.content_length))


def s3_to_s3_single(src: S3Object, dst: S3Object):
    s3 = boto3.resource("s3")
    dst_bucket = s3.Bucket(dst.bucket)
    src_bucket = s3.Bucket(src.bucket)

    src_obj = src_bucket.Object(src.key)
    src_dict = {"Bucket": src.bucket, "Key": src.key}
    dst_obj = dst_bucket.Object(dst.key)

    _s3_to_s3_check_etag(src_dict, src_obj, dst_obj)


S3ObjectWrapper = NamedTuple("S3ObjectWrapper", [("content_length", int), ("e_tag", str)])


def s3_to_s3_deep(src: S3Object, dst: S3Object):
    s3 = boto3.resource("s3")
    src_bucket = s3.Bucket(src.bucket)
    dst_bucket = s3.Bucket(dst.bucket)

    for obj in src_bucket.objects.filter(Prefix=src.key):
        src_dict = {"Bucket": src.bucket, "Key": obj.key}
        # replace the prefix
        dst_key = obj.key.replace(src.key, dst.key)
        dst_obj = dst_bucket.Object(dst_key)

        # Fake boto3 Object from boto3 ObjectSummary
        src_obj = S3ObjectWrapper(obj.size, obj.e_tag)

        _s3_to_s3_check_etag(src_dict, src_obj, dst_obj)


def s3_to_s3(src: str, dst: str, md5: Optional[str] = None) -> FetchedType:
    s3src = S3Object.parse(src)
    s3dst = S3Object.parse(dst)

    if is_s3_file(s3src):
        if md5:
            # This version does the validation just for a single s3-file
            transfer_to_s3(download_from_s3, src, dst, md5)
        else:
            s3_to_s3_single(s3src, s3dst)
        return FetchedType.FILE
    else:
        # For all other cases we just transfer
        s3_to_s3_deep(s3src, s3dst)
        return FetchedType.DIRECTORY
