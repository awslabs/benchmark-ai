from bai_kafka_utils.utils import md5sum


def get_dataset_dst(src: str, s3_bucket: str):
    return f"s3://{s3_bucket}/data_sets/{md5sum(src)}"
