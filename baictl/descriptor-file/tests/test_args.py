from transpiler.config import DescriptorConfig, BaiConfig
from transpiler.args import get_args, create_bai_config, create_descriptor_config


def test_args_azs(config_args):
    assert config_args.availability_zones == ['us-east-1a', 'us-east-1b', 'us-east-1c']


def test_list_arg(shared_datadir):
    required_args = "descriptor.toml --availability-zones=us-east-1a us-east-1b us-east-1c"
    args = get_args(f'--my-config {str(shared_datadir / "config.yaml")} ' + required_args)
    assert 'single_node' in args.valid_strategies


def test_create_descriptor_config(config_args):
    expected_config = DescriptorConfig(valid_strategies=config_args.valid_strategies)
    descriptor_config = create_descriptor_config(config_args)
    assert descriptor_config == expected_config


def test_create_bai_config(config_args):
    expected_config = BaiConfig(
        shared_memory_vol=config_args.shared_memory_vol,
        puller_docker_image=config_args.puller_docker_image,
        puller_mount_chmod=config_args.puller_mount_chmod,
        puller_s3_region=config_args.puller_s3_region
    )
    bai_config = create_bai_config(config_args)

    assert bai_config == expected_config
