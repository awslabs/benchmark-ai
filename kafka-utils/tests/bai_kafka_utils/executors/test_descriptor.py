import pytest

from bai_kafka_utils.executors.descriptor import DescriptorError, Descriptor


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


def test_find_data_source(descriptor):
    source = descriptor.find_data_source("foo1")
    assert source["path"] == "bar1"
