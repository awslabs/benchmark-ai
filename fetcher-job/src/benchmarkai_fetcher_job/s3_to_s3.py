import boto3

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


def s3_to_s3(src: str, dst: str):
    s3src = S3Object.parse(src)
    s3dst = S3Object.parse(dst)

    s3_to_s3_deep(s3src, s3dst)
