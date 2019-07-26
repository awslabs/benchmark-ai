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


def test_distributed_explicite(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["hardware"]["distributed"]["processes_per_instance"] = "4"
    descriptor = Descriptor(descriptor_as_dict, descriptor_config)

    assert descriptor.processes_per_instance == 4


def test_distributed_default(descriptor_as_dict, descriptor_config):
    descriptor = Descriptor(descriptor_as_dict, descriptor_config)

    assert descriptor.processes_per_instance == 1


def test_distributed_gpus(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["hardware"]["instance_type"] = "p3.8xlarge"
    descriptor_as_dict["hardware"]["distributed"]["processes_per_instance"] = "gpus"
    descriptor = Descriptor(descriptor_as_dict, descriptor_config)

    assert descriptor.processes_per_instance == 4


def test_distributed_gpus_on_cpu(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["hardware"]["instance_type"] = "t2.small"
    descriptor_as_dict["hardware"]["distributed"]["processes_per_instance"] = "gpus"

    with pytest.raises(DescriptorError):
        Descriptor(descriptor_as_dict, descriptor_config)
