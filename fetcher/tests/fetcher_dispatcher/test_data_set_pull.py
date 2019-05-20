import pytest

from bai_kafka_utils.events import DataSet
from fetcher_dispatcher.data_set_pull import get_dataset_dst

S3_BUCKET = "datasets_bucket"


@pytest.mark.parametrize(
    "data_set, expected",
    [
        # Simplest case
        (
            DataSet(src="http://some-server.org/datasets/plenty/bigfile.zip"),
            f"s3://{S3_BUCKET}/data_sets/390c2fe19f6061e4520964a1a968cede/datasets/plenty/bigfile.zip",
        ),
        # Same with query args - we ignore them
        (
            DataSet(src="http://some-server.org/datasets/plenty/bigfile.zip?foo=bar"),
            f"s3://{S3_BUCKET}/data_sets/5fddff4d49df672934851f436de903f3/datasets/plenty/bigfile.zip",
        ),
        # md5 matters
        (
            DataSet(src="http://some-server.org/datasets/plenty/bigfile.zip", md5="42"),
            f"s3://{S3_BUCKET}/data_sets/390c2fe19f6061e4520964a1a968cede/42/datasets/plenty/bigfile.zip",
        ),
        # Hardly possible, but who knows?
        (DataSet(src="http://some-server.org"), f"s3://{S3_BUCKET}/data_sets/a05fe609e976847b1543a2f3cd25d22c"),
    ],
    ids=["simple", "simple with query", "md5 matters", "no doc path"],
)
def test_simple_case(data_set: DataSet, expected: str):
    dst = get_dataset_dst(data_set, S3_BUCKET)
    assert dst == expected
