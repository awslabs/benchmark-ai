from transpiler.bai_knowledge import create_bai_k8s_builder, create_bai_data_sources


def test_add_container_cmd(descriptor, bai_config, fetched_data_sources, bai_environment_info):
    descriptor.benchmark_code = 'cmd'
    descriptor.ml_args = 'arg1 arg2'

    bai_k8s_builder = create_bai_k8s_builder(descriptor, bai_config, fetched_data_sources,
                                             environment_info=bai_environment_info)
    container = bai_k8s_builder.root.find_container('benchmark')
    assert container.command == ['cmd', 'arg1', 'arg2']
    assert 'args' not in container


def test_add_container_no_cmd(descriptor, bai_config, fetched_data_sources, bai_environment_info):
    descriptor.benchmark_code = ''
    descriptor.ml_args = 'arg1 arg2=abc'

    bai_k8s_builder = create_bai_k8s_builder(descriptor, bai_config, fetched_data_sources,
                                             environment_info=bai_environment_info)
    container = bai_k8s_builder.root.find_container('benchmark')
    assert 'command' not in container
    assert container.args == ['arg1', 'arg2=abc']


def test_create_bai_data_sources(fetched_data_sources, descriptor):
    bai_data_sources = create_bai_data_sources(fetched_data_sources, descriptor)

    for source in bai_data_sources:
        assert source.path == descriptor.find_data_source(source.src)['path']
