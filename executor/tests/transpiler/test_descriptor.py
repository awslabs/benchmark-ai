import pytest

from transpiler.descriptor import Descriptor, DescriptorError
import transpiler.bai_knowledge as bai_knowledge


@pytest.mark.parametrize("filename", ["missing_keys_descriptor.toml", "missing_section_descriptor.toml"])
def test_wrong_descriptor(datadir, filename, descriptor_config):
    with pytest.raises(DescriptorError):
        Descriptor.from_toml_file(str(datadir / filename), descriptor_config)


@pytest.mark.parametrize("scheduling", ["0 0 0 0", "* * ? * *", "single"])
def test_invalid_scheduling(descriptor, scheduling):
    descriptor.scheduling = scheduling
    with pytest.raises(DescriptorError):
        descriptor._validate()


def test_descriptor_config(descriptor_config):
    strategies = ["single_node", "horovod"]
    assert descriptor_config.valid_strategies == strategies


def test_find_data_source(descriptor, base_data_sources):
    source = descriptor.find_data_source(base_data_sources[0]["src"])
    assert source["path"] == base_data_sources[0]["path"]


def test_get_num_installed_gpus_valid_gpu():
    assert bai_knowledge._get_num_installed_gpus(instance_type="p3.8xlarge") == 4


def test_get_num_installed_gpus_invalid_gpu():
    with pytest.raises(Exception):
        bai_knowledge._get_num_installed_gpus(instance_type="p3.18000xlarge")


def test_get_num_installed_gpus_valid_cpu():
    assert bai_knowledge._get_num_installed_gpus(instance_type="c5.18xlarge") == 0


def test_get_num_installed_gpus_invalid_cpu():
    assert bai_knowledge._get_num_installed_gpus(instance_type="c5.18000xlarge") == 0
