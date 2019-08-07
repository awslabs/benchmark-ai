import addict
from bai_kafka_utils.kafka_service import KafkaService
from unittest.mock import create_autospec

from bai_kafka_utils.events import BenchmarkEvent

from bai_kafka_utils.executors.descriptor import DescriptorConfig, Descriptor
from pytest import fixture

from sm_executor.args import SageMakerExecutorConfig
from sm_executor.frameworks import TENSORFLOW_FRAMEWORK, MXNET_FRAMEWORK


@fixture
def descriptor_config() -> DescriptorConfig:
    return DescriptorConfig(
        valid_strategies=["single_node", "horovod"], valid_frameworks=[TENSORFLOW_FRAMEWORK, MXNET_FRAMEWORK]
    )


@fixture
def sagemaker_config(descriptor_config) -> SageMakerExecutorConfig:
    return SageMakerExecutorConfig(
        subnets=["subnet-1", "subnet-2"],
        security_group_ids=["sg-1"],
        s3_nodata="s3://somebucket/nodata",
        s3_output_bucket="output-bucket",
        sm_role="some_role",
        tmp_sources_dir="/tmp/dir",
        descriptor_config=descriptor_config,
    )


@fixture
def descriptor_as_dict(descriptor_config):
    return addict.Dict(
        spec_version="0.1.0",
        hardware=addict.Dict(instance_type="p3.8xlarge", strategy="single_node"),
        env=addict.Dict(docker_image="jlcont/benchmarking:270219"),
        ml=addict.Dict(
            benchmark_code="python /home/benchmark/image_classification.py",
            framework="tensorflow",
            framework_version="1.12",
        ),
        data=addict.Dict(sources=[addict.Dict(src="foo1", path="bar1"), addict.Dict(src="foo2", path="bar2")]),
    )


@fixture
def descriptor(descriptor_config, descriptor_as_dict):
    return Descriptor(descriptor_as_dict, descriptor_config)


@fixture
def benchmark_event():
    return BenchmarkEvent(
        action_id="ACTION_ID",
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="DONTCARE",
        client_username="DONTCARE",
        authenticated=False,
        tstamp=1556814924121,
        visited=[],
        type="DONTCARE",
        payload=None,
    )


@fixture
def mock_kafka_service():
    return create_autospec(KafkaService)
