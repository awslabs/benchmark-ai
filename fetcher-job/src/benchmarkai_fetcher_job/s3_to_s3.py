import boto3
from typing import Optional

from benchmarkai_fetcher_job.s3_utils import S3Object


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

    # TODO Check for a single file if md5 is ok

    s3_to_s3_deep(s3src, s3dst)


def is_s3_file(obj: S3Object):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(obj.bucket)

    first = True
    for sub_obj in bucket.objects.filter(Prefix=obj.key):
        if first:
            if sub_obj.key != obj.key:
                return False
        else:
            return False
    return True
