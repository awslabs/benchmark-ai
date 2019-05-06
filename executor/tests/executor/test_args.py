from transpiler.config import DescriptorConfig, BaiConfig, EnvironmentInfo
from executor.config import ExecutorConfig
from executor.args import get_args, create_bai_config, create_descriptor_config, create_executor_config


def test_args_azs(config_args):
    args = get_args(config_args)
    assert args.availability_zones == ["us-east-1a", "us-east-1b", "us-east-1c"]


def test_list_arg(config_args):
    args = get_args(config_args)
    assert args.valid_strategies == ["single_node", "horovod"]


def test_create_descriptor_config(config_args):
    args = get_args(config_args)
    expected_config = DescriptorConfig(valid_strategies=args.valid_strategies)
    descriptor_config = create_descriptor_config(args)
    assert descriptor_config == expected_config


def test_create_bai_config(config_args):
    args = get_args(config_args)
    expected_config = BaiConfig(
        puller_docker_image=args.puller_docker_image,
        puller_mount_chmod=args.puller_mount_chmod,
        puller_s3_region=args.puller_s3_region,
    )
    bai_config = create_bai_config(args)

    assert bai_config == expected_config


def test_create_transpiler_config(config_args):
    transpiler_config = create_executor_config(config_args)

    args = get_args(config_args)
    expected_descriptor_config = DescriptorConfig(valid_strategies=args.valid_strategies)
    expected_bai_config = BaiConfig(
        puller_docker_image=args.puller_docker_image,
        puller_mount_chmod=args.puller_mount_chmod,
        puller_s3_region=args.puller_s3_region,
    )
    expected_environment_info = EnvironmentInfo(availability_zones=args.availability_zones)
    expected_transpiler_config = ExecutorConfig(
        descriptor_config=expected_descriptor_config,
        bai_config=expected_bai_config,
        environment_info=expected_environment_info,
        kubectl=args.kubectl,
    )

    assert transpiler_config == expected_transpiler_config
