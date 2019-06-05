import textwrap
import toml
import pytest

from unittest.mock import create_autospec
from _pytest.fixtures import fixture

from bai_kafka_utils.events import (
    DataSet,
    BenchmarkDoc,
    FetcherPayload,
    BenchmarkEvent,
    create_from_object,
    FetcherBenchmarkEvent,
)
from bai_kafka_utils.kafka_service import KafkaServiceConfig, KafkaService
from executor.args import create_executor_config
from executor.executor import ExecutorEventHandler
from transpiler.descriptor import Descriptor, DescriptorConfig
from transpiler.bai_knowledge import EnvironmentInfo
from transpiler.config import BaiConfig


ACTION_ID = "ACTION_ID"


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
    required_args = (
        "--descriptor=descriptor.toml --availability-zones=us-east-1a,us-east-1b,us-east-1c --kubectl=kubectl/path"
    )
    return f'{required_args} -c {str(shared_datadir / "default_config.yaml")}'


@pytest.fixture
def descriptor_config():
    config_values = {"valid_strategies": ["single_node", "horovod"], "valid_execution_engines": ["kubernetes"]}

    return DescriptorConfig(**config_values)


@pytest.fixture
def bai_config():
    return BaiConfig(puller_mount_chmod="700", puller_s3_region="s3_region", puller_docker_image="test/docker:image")


@pytest.fixture
def descriptor_string(base_data_sources):
    return textwrap.dedent(
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


@pytest.fixture
def descriptor_dict(descriptor_string):
    return toml.loads(descriptor_string)


@pytest.fixture
def descriptor(descriptor_config, descriptor_dict):
    return Descriptor(descriptor_dict, descriptor_config)


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
def benchmark_doc(descriptor_dict, descriptor_string) -> BenchmarkDoc:
    return BenchmarkDoc(contents=descriptor_dict, doc=descriptor_string, sha1="123")


@pytest.fixture
def benchmark_event_with_data_sets(benchmark_event, benchmark_doc: BenchmarkDoc) -> FetcherBenchmarkEvent:
    payload = FetcherPayload(
        toml=benchmark_doc,
        datasets=[DataSet(src="src1", dst="s3://bucket/object"), DataSet(src="src2", dst="s3://bucket/object2")],
    )
    return create_from_object(FetcherBenchmarkEvent, benchmark_event, payload=payload)


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


@fixture
def executor_callback(config_args, kafka_service_config) -> ExecutorEventHandler:
    config = create_executor_config(config_args)
    return ExecutorEventHandler(config, kafka_service_config.producer_topic)
