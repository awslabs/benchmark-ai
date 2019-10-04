import json
import textwrap

import toml
import pytest
from bai_kafka_utils.executors.descriptor import Descriptor, DescriptorConfig, DistributedStrategy

from unittest.mock import create_autospec

from bai_kafka_utils.events import DownloadableContent, BenchmarkDoc, FetcherPayload, BenchmarkEvent
from bai_kafka_utils.kafka_service import KafkaServiceConfig, KafkaService
from transpiler.bai_knowledge import EnvironmentInfo
from transpiler.config import BaiConfig

AVAILABILITY_ZONES = {"use1-az1": "us-east-1a", "use1-az2": "us-east-1b", "use1-az3": "us-east-1c"}

ACTION_ID = "ACTION_ID"


@pytest.fixture
def mock_availability_zones():
    return AVAILABILITY_ZONES


@pytest.fixture
def base_data_sources():
    return [
        {
            "src": "s3://mlperf-data-stsukrov/imagenet/train-480px",
            "md5": "md5",
            "path": "/data/tf-imagenet/train",
            "puller_uri": "s3://puller-data-stsukrov/imagenet/train",
        },
        {
            "src": "s3://mlperf-data-stsukrov/imagenet/validation-480px",
            "md5": "md5",
            "path": "/data/tf-imagenet/validation",
            "puller_uri": "s3://puller-data-stsukrov/imagenet/validation",
        },
    ]


@pytest.fixture
def bai_environment_info():
    return EnvironmentInfo(availability_zones=AVAILABILITY_ZONES)


@pytest.fixture
def fetched_data_sources(base_data_sources):
    sources = []

    for source in base_data_sources:
        sources.append(
            DownloadableContent(src=source["src"], path="/mount/path", md5=source["md5"], dst=source["puller_uri"])
        )
    return sources


@pytest.fixture
def config_args(shared_datadir):
    required_args = "--descriptor=descriptor.toml " + "--kubectl=kubectl/path"
    return f'{required_args} -c {str(shared_datadir / "default_config.yaml")}'


@pytest.fixture
def config_env():
    return {"AVAILABILITY_ZONES": json.dumps(AVAILABILITY_ZONES)}


@pytest.fixture
def descriptor_config():
    config_values = {
        "valid_strategies": [e.value for e in DistributedStrategy],
        "valid_frameworks": ["", "mxnet", "tensorflow"],
    }
    return DescriptorConfig(**config_values)


@pytest.fixture
def bai_config():
    return BaiConfig(
        puller_mount_chmod="700",
        puller_docker_image="test/puller:image",
        metrics_pusher_docker_image="test/metrics_pusher:image",
        metrics_extractor_docker_image="test/metrics_extractor:image",
        job_status_trigger_docker_image="test/job_status_trigger:image",
        cron_job_docker_image="test/cron_job:image",
        suppress_job_affinity=True,
    )


@pytest.fixture
def descriptor_as_dict(descriptor_config, base_data_sources):
    return toml.loads(
        textwrap.dedent(
            fr"""
        spec_version = "0.1.0"
        [info]
        task_name = "Title"
        description = "Description"
        [hardware]
        instance_type = 'p3.8xlarge'
        strategy = 'single_node'
        [env]
        docker_image = 'jlcont/benchmarking:270219'
        privileged = false
        extended_shm = true
        [ml]
        benchmark_code = 'python /home/benchmark/image_classification.py'
        args = '--model=resnet50_v2 --batch-size=32'
        [data]
        id = 'mnist'
        [[data.sources]]
        src = '{base_data_sources[0]['src']}'
        path = '{base_data_sources[0]['path']}'
        [[data.sources]]
        src = '{base_data_sources[1]['src']}'
        path = '{base_data_sources[1]['path']}'
        [output]
        [[output.metrics]]
        name = "accuracy"
        unit = "%"
        pattern = "accuracy=([-+]?\\d*\\.\\d+|\\d+)"
        [[output.metrics]]
        name = "throughput"
        unit = "images/sec"
        pattern = "throughput=([-+]?\\d*\\.\\d+|\\d+)"
        """
        )
    )


@pytest.fixture
def descriptor(descriptor_config, descriptor_as_dict):
    return Descriptor(descriptor_as_dict, descriptor_config)


@pytest.fixture
def benchmark_event(shared_datadir):
    descriptor_path = str(shared_datadir / "hello-world.toml")
    descriptor_as_dict = toml.load(descriptor_path)
    doc = BenchmarkDoc(contents=descriptor_as_dict, sha1="SHA1", doc="doc")

    payload = FetcherPayload(toml=doc, datasets=[])

    return BenchmarkEvent(
        action_id=ACTION_ID,
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="CLIENT_VERSION",
        client_username="client_username",
        authenticated=False,
        tstamp=42,
        visited=[],
        type="BAI_APP_FETCHER",
        payload=payload,
    )


@pytest.fixture
def kafka_service_config():
    return KafkaServiceConfig(
        consumer_group_id="CONSUMER_GROUP_ID",
        producer_topic="BAI_APP_FETCHER",
        consumer_topic="BAI_APP_EXECUTOR",
        bootstrap_servers=["localhost:9092"],
        logging_level="INFO",
        cmd_submit_topic="CMD_SUBMIT",
        cmd_return_topic="CMD_RETURN",
        status_topic="BAI_APP_STATUS",
    )


@pytest.fixture
def kafka_service() -> KafkaService:
    return create_autospec(KafkaService)
