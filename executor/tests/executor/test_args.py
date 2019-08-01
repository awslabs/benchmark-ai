from bai_kafka_utils.executors.descriptor import DescriptorConfig, DistributedStrategy

from transpiler.config import BaiConfig, EnvironmentInfo

from executor.config import ExecutorConfig
from executor.args import get_args, create_bai_config, create_descriptor_config, create_executor_config


def test_args_azs(config_args, config_env, mock_availability_zones):
    args = get_args(config_args, config_env)
    assert args.availability_zones == mock_availability_zones


def test_list_arg(config_args, config_env):
    args = get_args(config_args, config_env)
    assert args.valid_strategies == [e.value for e in DistributedStrategy]


def test_default_frameworks(config_args, config_env):
    args = get_args(config_args, config_env)
    assert set(args.valid_frameworks) == {"", "mxnet", "tensorflow"}


def test_create_descriptor_config(config_args, config_env):
    args = get_args(config_args, config_env)
    expected_config = DescriptorConfig(valid_strategies=args.valid_strategies, valid_frameworks=args.valid_frameworks)
    descriptor_config = create_descriptor_config(args)
    assert descriptor_config == expected_config


def test_create_bai_config(config_args, config_env):
    args = get_args(config_args, config_env)
    expected_config = BaiConfig(
        puller_docker_image=args.puller_docker_image,
        puller_mount_chmod=args.puller_mount_chmod,
        metrics_pusher_docker_image=args.metrics_pusher_docker_image,
        cron_job_docker_image=args.cron_job_docker_image,
    )
    bai_config = create_bai_config(args)

    assert bai_config == expected_config


def test_create_executor_config(config_args, config_env, mock_availability_zones):
    executor_config = create_executor_config(config_args, config_env)

    args = get_args(config_args, config_env)
    expected_descriptor_config = DescriptorConfig(
        valid_strategies=args.valid_strategies, valid_frameworks=args.valid_frameworks
    )
    expected_bai_config = BaiConfig(
        puller_docker_image=args.puller_docker_image,
        puller_mount_chmod=args.puller_mount_chmod,
        metrics_pusher_docker_image=args.metrics_pusher_docker_image,
        cron_job_docker_image=args.cron_job_docker_image,
    )
    expected_environment_info = EnvironmentInfo(mock_availability_zones)
    expected_executor_config = ExecutorConfig(
        descriptor_config=expected_descriptor_config,
        bai_config=expected_bai_config,
        environment_info=expected_environment_info,
        kubectl=args.kubectl,
    )

    assert executor_config == expected_executor_config
