from transpiler.bai_knowledge import create_bai_k8s_builder


def test_add_container_cmd(descriptor, bai_environment_info, bai_config):
    descriptor.benchmark_code = 'cmd'
    descriptor.ml_args = 'arg1 arg2'

    bai_k8s_builder = create_bai_k8s_builder(descriptor, bai_config, environment_info=bai_environment_info)
    container = bai_k8s_builder.root.find_container('benchmark')
    assert container.command == ['cmd', 'arg1', 'arg2']
    assert 'args' not in container


def test_add_container_no_cmd(descriptor, bai_environment_info, bai_config):
    descriptor.benchmark_code = ''
    descriptor.ml_args = 'arg1 arg2=abc'

    bai_k8s_builder = create_bai_k8s_builder(descriptor, bai_config, environment_info=bai_environment_info)
    container = bai_k8s_builder.root.find_container('benchmark')
    assert 'command' not in container
    assert container.args == ['arg1', 'arg2=abc']
