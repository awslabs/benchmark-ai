from transpiler.args import get_args

REQUIRED_ARGS = "descriptor.toml --availability-zones=us-east-1a,us-east-1b,us-east-1c"


def test_list_arg(shared_datadir):
    args = get_args(f'--my-config {str(shared_datadir / "config.yaml")} ' + REQUIRED_ARGS)
    assert args.valid_data_sources == ['s1', 's2', 's3']
    assert 'single_node' in args.valid_strategies
