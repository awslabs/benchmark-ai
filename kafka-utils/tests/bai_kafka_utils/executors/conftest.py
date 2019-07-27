import pytest
from addict import addict

from bai_kafka_utils.executors.descriptor import Descriptor, DescriptorConfig, DistributedStrategy


@pytest.fixture
def descriptor_config():
    return DescriptorConfig(
        valid_strategies=[e.value for e in DistributedStrategy], valid_frameworks=["", "mxnet", "tensorflow"]
    )


@pytest.fixture
def descriptor_as_dict(descriptor_config):
    return addict.Dict(
        spec_version="0.1.0",
        hardware=addict.Dict(instance_type="p3.8xlarge", strategy="single_node"),
        env=addict.Dict(docker_image="jlcont/benchmarking:270219"),
        ml=addict.Dict(benchmark_code="python /home/benchmark/image_classification.py"),
        data=addict.Dict(sources=[addict.Dict(src="foo1", path="bar1"), addict.Dict(src="foo2", path="bar2")]),
    )


@pytest.fixture
def descriptor(descriptor_config, descriptor_as_dict):
    return Descriptor(descriptor_as_dict, descriptor_config)
