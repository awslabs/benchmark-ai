from transpiler.config import BaiConfig, EnvironmentInfo, AvailabilityZoneInfo
from transpiler.descriptor import DescriptorConfig
from executor.config import ExecutorConfig
from executor.args import get_args, create_bai_config, create_descriptor_config, create_executor_config

ZONE_IDS = ["use1-az1", "use1-az2", "use1-az3"]

ZONE_NAMES = ["us-east-1a", "us-east-1b", "us-east-1c"]

ZONES = [AvailabilityZoneInfo(name, zone_id) for name, zone_id in zip(ZONE_NAMES, ZONE_IDS)]


def test_args_azs(config_args):
    args = get_args(config_args)
    assert args.availability_zones_names == ZONE_NAMES
    assert args.availability_zones_ids == ZONE_IDS


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


def test_create_executor_config(config_args):
    executor_config = create_executor_config(config_args)

    args = get_args(config_args)
    expected_descriptor_config = DescriptorConfig(valid_strategies=args.valid_strategies)
    expected_bai_config = BaiConfig(
        puller_docker_image=args.puller_docker_image,
        puller_mount_chmod=args.puller_mount_chmod,
        puller_s3_region=args.puller_s3_region,
    )
    expected_environment_info = EnvironmentInfo(ZONES)
    expected_executor_config = ExecutorConfig(
        descriptor_config=expected_descriptor_config,
        bai_config=expected_bai_config,
        environment_info=expected_environment_info,
        kubectl=args.kubectl,
    )

    assert executor_config == expected_executor_config
