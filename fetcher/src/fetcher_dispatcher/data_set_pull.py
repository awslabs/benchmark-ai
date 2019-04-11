import os

from fetcher_dispatcher.utils import md5sum

S3_BUCKET = os.environ.get("S3_DATASET_BUCKET")


def get_dataset_dst(src: str):
    return f"s3://{S3_BUCKET}/datasets/{md5sum(src)}"
