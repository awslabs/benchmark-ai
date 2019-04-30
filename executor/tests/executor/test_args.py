import pytest

from transpiler.config import DescriptorConfig, BaiConfig, TranspilerConfig, EnvironmentInfo
from executor.args import get_args, create_bai_config, create_descriptor_config, create_transpiler_config


@pytest.fixture
def config_args(shared_datadir):
    required_args = "--descriptor=descriptor.toml --availability-zones=us-east-1a us-east-1b us-east-1c"
    return f'{required_args} -c {str(shared_datadir / default_config.yaml)}'


def test_args_azs(config_args):
    args = get_args(config_args)
    assert args.availability_zones == ['us-east-1a', 'us-east-1b', 'us-east-1c']


def test_list_arg(config_args):
    args = get_args(config_args)
    assert args.valid_strategies == ['single_node', 'horovod']


def test_create_descriptor_config(config_args):
    args = get_args(config_args)
    expected_config = DescriptorConfig(valid_strategies=args.valid_strategies)
    descriptor_config = create_descriptor_config(args)
    assert descriptor_config == expected_config


def test_create_bai_config(config_args):
    args = get_args(config_args)
    expected_config = BaiConfig(
        shared_memory_vol=args.shared_memory_vol,
        puller_docker_image=args.puller_docker_image,
        puller_mount_chmod=args.puller_mount_chmod,
        puller_s3_region=args.puller_s3_region
    )
    bai_config = create_bai_config(args)

    assert bai_config == expected_config


def test_create_transpiler_config(config_args):
    transpiler_config = create_transpiler_config(config_args)

    args = get_args(config_args)
    expected_descriptor_config = DescriptorConfig(valid_strategies=args.valid_strategies)
    expected_bai_config = BaiConfig(
        shared_memory_vol=args.shared_memory_vol,
        puller_docker_image=args.puller_docker_image,
        puller_mount_chmod=args.puller_mount_chmod,
        puller_s3_region=args.puller_s3_region
    )
    expected_environment_info = EnvironmentInfo(
        availability_zones=args.availability_zones
    )
    expected_transpiler_config = TranspilerConfig(
        descriptor=args.descriptor,
        filename=args.filename,
        descriptor_config=expected_descriptor_config,
        bai_config=expected_bai_config,
        environment_info=expected_environment_info
    )

    assert transpiler_config == expected_transpiler_config
