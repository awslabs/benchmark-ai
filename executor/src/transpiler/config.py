from dataclasses import dataclass
from urllib.parse import urlparse

from bai_kafka_utils.events import DataSet, FileSystemObject
from bai_kafka_utils.executors.descriptor import DescriptorError
from typing import Dict


@dataclass
class BaiConfig:
    puller_mount_chmod: str
    puller_docker_image: str
    cron_job_docker_image: str
    metrics_pusher_docker_image: str
    metrics_extractor_docker_image: str
    job_status_trigger_docker_image: str
    suppress_job_affinity: bool = False


@dataclass
class EnvironmentInfo:
    """
    Holds information on the environment that BAI is running.
    It is meant to aid in making decisions on how to run the benchmarks.
    """

    availability_zones: Dict[str, str]


@dataclass(init=False)
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
            raise DescriptorError(
                f"Unexpected scheme in data source src: {self.scheme}." f" Fetched dataset is {fetched_data_source}"
            )


@dataclass(init=False)
class BaiScriptSource:
    scheme: str
    bucket: str
    object: str

    def __init__(self, fetched_script: FileSystemObject):
        parsed_uri = urlparse(fetched_script.dst)
        self.scheme = parsed_uri.scheme
        self.bucket = parsed_uri.netloc
        self.object = parsed_uri.path[1:]

        if self.scheme.lower() != "s3":
            raise DescriptorError(
                f"Unexpected scheme in script src: {self.scheme}." f" Fetched script is {fetched_script}"
            )
