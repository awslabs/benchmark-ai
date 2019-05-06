import textwrap
import uuid

import toml
import pytest

from bai_kafka_utils.events import DataSet, BenchmarkDoc, FetcherPayload, BenchmarkEvent
from transpiler.descriptor import Descriptor
from transpiler.bai_knowledge import EnvironmentInfo
from transpiler.config import DescriptorConfig, BaiConfig


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
    return EnvironmentInfo(availability_zones=["us-east-1a", "us-east-1b", "us-east-1c"])


@pytest.fixture
def fetched_data_sources(base_data_sources):
    sources = []

    for source in base_data_sources:
        sources.append(DataSet(src=source["src"], md5=source["md5"], dst=source["puller_uri"]))
    return sources


@pytest.fixture
def config_args(shared_datadir):
    required_args = "--descriptor=descriptor.toml --availability-zones=us-east-1a,us-east-1b,us-east-1c --kubeconfig=kubeconfig/path"
    return f'{required_args} -c {str(shared_datadir / "default_config.yaml")}'


@pytest.fixture
def descriptor_config():
    config_values = {"valid_strategies": ["single_node", "horovod"]}

    return DescriptorConfig(**config_values)


@pytest.fixture
def bai_config():
    return BaiConfig(puller_mount_chmod="700", puller_s3_region="s3_region", puller_docker_image="test/docker:image")


@pytest.fixture
def descriptor(descriptor_config, base_data_sources):
    return Descriptor(
        toml.loads(
            textwrap.dedent(
                f"""\
        spec_version = '0.1.0'
        [info]
        task_name = 'Title'
        description = 'Description'
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
    """
            )
        ),
        descriptor_config,
    )


@pytest.fixture
def benchmark_event(shared_datadir):
    descriptor_path = str(shared_datadir / "hello-world.toml")
    descriptor_as_dict = toml.load(descriptor_path)
    doc = BenchmarkDoc(contents=descriptor_as_dict, sha1="SHA1", doc="doc")

    payload = FetcherPayload(toml=doc, datasets=[])

    return BenchmarkEvent(
        action_id=uuid.uuid4().hex,
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="CLIENT_VERSION",
        client_username="client_username",
        authenticated=False,
        tstamp=42,
        visited=[],
        payload=payload,
    )
