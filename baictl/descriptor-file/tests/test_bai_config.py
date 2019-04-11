import textwrap
import toml

import pytest

from transpiler.descriptor import Descriptor
from transpiler.bai_knowledge import BaiConfig, create_bai_config


@pytest.fixture
def descriptor():
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
    """)))


def test_add_container_cmd(descriptor, bai_environment_info):
    descriptor.benchmark_code = 'cmd'
    descriptor.ml_args = 'arg1 arg2'

    baiconfig = create_bai_config(descriptor, environment_info=bai_environment_info)
    container = baiconfig.root.find_container('benchmark')
    assert container.command == ['cmd', 'arg1', 'arg2']
    assert 'args' not in container


def test_add_container_no_cmd(descriptor, bai_environment_info):
    descriptor.benchmark_code = ''
    descriptor.ml_args = 'arg1 arg2=abc'

    baiconfig = create_bai_config(descriptor, environment_info=bai_environment_info)
    container = baiconfig.root.find_container('benchmark')
    assert 'command' not in container
    assert container.args == ['arg1', 'arg2=abc']
