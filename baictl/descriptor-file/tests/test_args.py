from transpiler.args import get_args


def test_args_azs(config_args):
    assert config_args.availability_zones == ['us-east-1a', 'us-east-1b', 'us-east-1c']


def test_list_arg(shared_datadir):
    required_args = "descriptor.toml --availability-zones=us-east-1a us-east-1b us-east-1c"
    args = get_args(f'--my-config {str(shared_datadir / "config.yaml")} ' + required_args)
    assert args.valid_data_sources == ['s1', 's2', 's3']
    assert 'single_node' in args.valid_strategies
