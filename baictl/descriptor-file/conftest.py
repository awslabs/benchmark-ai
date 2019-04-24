import textwrap
import toml

import pytest

from transpiler.descriptor import Descriptor, DescriptorConfig
from transpiler.bai_knowledge import EnvironmentInfo

@pytest.fixture
def bai_environment_info():
    return EnvironmentInfo(
        availability_zones=["us-east-1a", "us-east-1b", "us-east-1c"]
    )


@pytest.fixture
def descriptor_config():
    config_values = {'VALID_DATA_SOURCES': '["s3", "http", "https", "ftp", "ftps"]',
                     'VALID_STRATEGIES': '["single_node", "horovod"]'}
    return DescriptorConfig(**config_values)


@pytest.fixture
def descriptor(descriptor_config):
    return Descriptor(toml.loads(textwrap.dedent("""\
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
        uri = 's3://mlperf-data-stsukrov/imagenet/train-480px'
        path = '~/data/tf-imagenet/'
        [[data.sources]]
        uri = 's3://mlperf-data-stsukrov/imagenet/validation-480px'
        path = '~/data/tf-imagenet/'
    """)), descriptor_config)
