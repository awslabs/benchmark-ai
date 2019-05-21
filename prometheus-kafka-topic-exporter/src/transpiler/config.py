from dataclasses import dataclass
from urllib.parse import urlparse
from bai_kafka_utils.events import DataSet
from typing import List


@dataclass
class DescriptorConfig:
    valid_strategies: List[str]


@dataclass
class BaiConfig:
    puller_mount_chmod: str
    puller_s3_region: str
    puller_docker_image: str


@dataclass
class EnvironmentInfo:
    """
    Holds information on the environment that BAI is running.
    It is meant to aid in making decisions on how to run the benchmarks.
    """

    availability_zones: List[str]


@dataclass
class BaiDataSource:
    scheme: str
    bucket: str
    object: str
    path: str

    def __init__(self, fetched_data_source: DataSet, path: str):
        parsed_uri = urlparse(fetched_data_source.dst)
        self.src = fetched_data_source.src
        self.scheme = parsed_uri.scheme
        self.bucket = parsed_uri.netloc
        self.object = parsed_uri.path[1:]
        self.path = path

        if self.scheme.lower() != "s3":
            raise ValueError(
                f"Unexpected scheme in data source src: {self.scheme}." f" Fetched dataset is {fetched_data_source}"
            )
