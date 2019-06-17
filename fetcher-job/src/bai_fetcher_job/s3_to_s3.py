import boto3
from typing import Optional

from bai_fetcher_job.s3_utils import S3Object, download_from_s3, is_s3_file
from bai_fetcher_job.transfer_to_s3 import transfer_to_s3


# Initial version of the folder transfer, that lacks validation
# TODO Implement Merkl-tree or something like that


def s3_to_s3_single(src: S3Object, dst: S3Object):
    s3 = boto3.resource("s3")
    old_bucket = s3.Bucket(src.bucket)
    new_bucket = s3.Bucket(dst.bucket)
    old_source = {"Bucket": src.bucket, "Key": src.key}
    new_obj = new_bucket.Object(dst.key)
    new_obj.copy(old_source)


def s3_to_s3_deep(src: S3Object, dst: S3Object):
    s3 = boto3.resource("s3")
    old_bucket = s3.Bucket(src.bucket)
    new_bucket = s3.Bucket(dst.bucket)

    for obj in old_bucket.objects.filter(Prefix=src.key):
        old_source = {"Bucket": src.bucket, "Key": obj.key}
        # replace the prefix
        new_key = obj.key.replace(src.key, dst.key)
        new_obj = new_bucket.Object(new_key)

        new_obj.copy(old_source)


def s3_to_s3(src: str, dst: str, md5: Optional[str] = None):
    s3src = S3Object.parse(src)
    s3dst = S3Object.parse(dst)

    if is_s3_file(s3src):
        if md5:
            # This version does the validation just for a single s3-file
            transfer_to_s3(download_from_s3, src, dst, md5)
        else:
            s3_to_s3_single(s3src, s3dst)
    else:
        # For all other cases we just transfer
        s3_to_s3_deep(s3src, s3dst)
