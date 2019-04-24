from transpiler.bai_knowledge import create_bai_config


<<<<<<< HEAD
def test_add_container_cmd(descriptor, bai_environment_info, config_args):
    descriptor.benchmark_code = 'cmd'
    descriptor.ml_args = 'arg1 arg2'

    baiconfig = create_bai_config(descriptor, config_args, environment_info=bai_environment_info)
=======
def test_add_container_cmd(descriptor, bai_environment_info, config):
    descriptor.benchmark_code = 'cmd'
    descriptor.ml_args = 'arg1 arg2'

    baiconfig = create_bai_config(descriptor, config, environment_info=bai_environment_info)
>>>>>>> [baictl] Added tests for external settings.ini file
    container = baiconfig.root.find_container('benchmark')
    assert container.command == ['cmd', 'arg1', 'arg2']
    assert 'args' not in container


<<<<<<< HEAD
def test_add_container_no_cmd(descriptor, bai_environment_info, config_args):
    descriptor.benchmark_code = ''
    descriptor.ml_args = 'arg1 arg2=abc'

    baiconfig = create_bai_config(descriptor, config_args, environment_info=bai_environment_info)
=======
def test_add_container_no_cmd(descriptor, bai_environment_info, config):
    descriptor.benchmark_code = ''
    descriptor.ml_args = 'arg1 arg2=abc'

    baiconfig = create_bai_config(descriptor, config, environment_info=bai_environment_info)
>>>>>>> [baictl] Added tests for external settings.ini file
    container = baiconfig.root.find_container('benchmark')
    assert 'command' not in container
    assert container.args == ['arg1', 'arg2=abc']
