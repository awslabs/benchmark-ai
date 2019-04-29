from dataclasses import dataclass
from urllib.parse import urlparse
from bai_kafka_utils.events import DataSet
from typing import List


@dataclass
class DescriptorConfig:
    valid_strategies: List[str]


@dataclass
class BaiConfig:
    shared_memory_vol: str
    puller_mount_chmod: str
    puller_s3_region: str
    puller_docker_image: str


@dataclass
class BaiDataSource:
    scheme: str
    bucket: str
    object: str
    path: str

    def __init__(self,
                 fetched_data_source: DataSet,
                 path: str):
        parsed_uri = urlparse(fetched_data_source.dst)
        self.src = fetched_data_source.uri
        self.scheme = parsed_uri.scheme
        self.bucket = parsed_uri.netloc
        self.object = parsed_uri.path[1:]
        self.path = path

        if self.scheme.lower() != 's3':
            raise ValueError(f'Unexpected scheme in data source uri: {self.scheme}.'
                             f' Fetched dataset is {fetched_data_source}')
