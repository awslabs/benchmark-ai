import pytest

from transpiler.descriptor import Descriptor, DescriptorError
import util.ec2_instance_info as ec2_instance_info


@pytest.mark.parametrize("filename", ["missing_keys_descriptor.toml", "missing_section_descriptor.toml"])
def test_wrong_descriptor(datadir, filename, descriptor_config):
    with pytest.raises(DescriptorError):
        Descriptor.from_toml_file(str(datadir / filename), descriptor_config)


@pytest.mark.parametrize("filename", ["minimal_descriptor.toml"])
def test_minimal_descriptor(datadir, filename, descriptor_config):
    Descriptor.from_toml_file(str(datadir / filename), descriptor_config)


@pytest.mark.parametrize("scheduling", ["0 0 0 0", "* * ? * *", "single"])
def test_invalid_scheduling(descriptor, scheduling):
    descriptor.scheduling = scheduling
    with pytest.raises(DescriptorError):
        descriptor._validate()


def test_descriptor_config(descriptor_config):
    strategies = ["single_node", "horovod"]
    assert descriptor_config.valid_strategies == strategies


def test_invalid_args_type(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["ml"]["args"] = 4
    with pytest.raises(DescriptorError):
        Descriptor(descriptor_as_dict, descriptor_config)


def test_find_data_source(descriptor, base_data_sources):
    source = descriptor.find_data_source(base_data_sources[0]["src"])
    assert source["path"] == base_data_sources[0]["path"]


def test_get_num_installed_gpus_valid_gpu():
    assert ec2_instance_info.get_instance_gpus(instance_type="p3.8xlarge") == 4


def test_get_num_installed_gpus_invalid_gpu():
    with pytest.raises(Exception):
        ec2_instance_info.get_instance_gpus(instance_type="p3.18000xlarge")


def test_get_num_installed_gpus_valid_cpu():
    assert ec2_instance_info.get_instance_gpus(instance_type="c5.18xlarge") == 0


def test_get_num_installed_gpus_invalid_cpu():
    assert ec2_instance_info.get_instance_gpus(instance_type="c5.18000xlarge") == 0
