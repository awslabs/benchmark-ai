from urllib.parse import urlparse

from bai_kafka_utils.events import DataSet
from bai_kafka_utils.utils import md5sum


def get_dataset_dst(data_set: DataSet, s3_bucket: str):
    # Req 1 - same dataset with different hashes should get different dest
    # Req 2 - at least some grade of human readability
    s3uri = f"s3://{s3_bucket}/data_sets/{md5sum(data_set.src)}"

    if data_set.md5:
        s3uri += f"/{data_set.md5}"

    parsed = urlparse(data_set.src)
    if parsed.path:
        s3uri += parsed.path

    return s3uri
