from transpiler.bai_knowledge import create_bai_config


def test_add_container_cmd(descriptor, bai_environment_info, config):
    descriptor.benchmark_code = 'cmd'
    descriptor.ml_args = 'arg1 arg2'

    baiconfig = create_bai_config(descriptor, config, environment_info=bai_environment_info)
    container = baiconfig.root.find_container('benchmark')
    assert container.command == ['cmd', 'arg1', 'arg2']
    assert 'args' not in container


def test_add_container_no_cmd(descriptor, bai_environment_info, config):
    descriptor.benchmark_code = ''
    descriptor.ml_args = 'arg1 arg2=abc'

    baiconfig = create_bai_config(descriptor, config, environment_info=bai_environment_info)
    container = baiconfig.root.find_container('benchmark')
    assert 'command' not in container
    assert container.args == ['arg1', 'arg2=abc']
