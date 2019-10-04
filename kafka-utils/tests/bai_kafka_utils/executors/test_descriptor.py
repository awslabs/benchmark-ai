import pytest

from bai_kafka_utils.executors.descriptor import DescriptorError, Descriptor, ONE_PER_GPU, DistributedStrategy


@pytest.mark.parametrize(
    "filename",
    [
        "missing_keys_descriptor.toml",
        "missing_section_descriptor.toml",
        "cs_missing_server_section_descriptor.toml",
        "cs_missing_docker_image_descriptor.toml",
        "cs_missing_hardware_descriptor.toml",
        "cs_missing_ports_descriptor.toml",
        "cs_missing_start_command_descriptor.toml",
        "cs_non_uri_liveliness_probe_descriptor.toml",
        "cs_non_uri_readiness_probe_descriptor.toml",
        "cs_missing_server_model_path_descriptor.toml",
        "cs_missing_server_model_src_descriptor.toml",
        "cs_missing_server_output_metrics_descriptor.toml",
        "cs_missing_server_output_metric_name_descriptor.toml",
        "cs_missing_server_output_metric_units_descriptor.toml",
        "cs_missing_server_output_metric_pattern_descriptor.toml",
    ],
)
def test_wrong_descriptor(datadir, filename, descriptor_config):
    with pytest.raises(DescriptorError):
        Descriptor.from_toml_file(str(datadir / filename), descriptor_config)


@pytest.mark.parametrize(
    "filename",
    [
        "minimal_descriptor.toml",
        "cs_minimal_descriptor.toml",
        "cs_with_optionals_descriptor.toml",
        "cs_minimal_with_models_descriptor.toml",
    ],
)
def test_minimal_descriptor(datadir, filename, descriptor_config):
    Descriptor.from_toml_file(str(datadir / filename), descriptor_config)


@pytest.mark.parametrize("scheduling", ["0 0 0 0", "* * ? * *", "single"])
def test_invalid_scheduling(descriptor, scheduling):
    descriptor.scheduling = scheduling
    with pytest.raises(DescriptorError):
        descriptor._validate()


@pytest.mark.parametrize(
    "labels",
    [
        {"-invalid": ""},
        {"invalid_": ""},
        {"valid": "_invalid"},
        {"": "aa"},
        {"more-than-63-chars-00025-00000-00038-00000-00000-00056-00000-00066": ""},
        {"a": "more-than-63-chars-00025-00000-00038-00000-00000-00056-00000-00066"},
    ],
)
def test_invalid_custom_labels(descriptor, labels):
    descriptor.custom_labels = labels
    with pytest.raises(DescriptorError):
        descriptor._validate()


def test_descriptor_config(descriptor_config):
    strategies = [e.value for e in DistributedStrategy]
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
    descriptor_as_dict["hardware"]["distributed"]["processes_per_instance"] = ONE_PER_GPU
    descriptor = Descriptor(descriptor_as_dict, descriptor_config)

    assert descriptor.processes_per_instance == 4


def test_distributed_gpus_on_cpu(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["hardware"]["instance_type"] = "t2.small"
    descriptor_as_dict["hardware"]["distributed"]["processes_per_instance"] = ONE_PER_GPU

    with pytest.raises(DescriptorError):
        Descriptor(descriptor_as_dict, descriptor_config)


def test_distributed_num_instances_str(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["hardware"]["distributed"]["num_instances"] = "4"
    descriptor = Descriptor(descriptor_as_dict, descriptor_config)

    assert descriptor.num_instances == 4


def test_distributed_num_instances_default(descriptor_as_dict, descriptor_config):
    descriptor = Descriptor(descriptor_as_dict, descriptor_config)

    assert descriptor.num_instances == 1


def test_framework_optional(descriptor_as_dict, descriptor_config):
    assert "" in descriptor_config.valid_frameworks
    descriptor_as_dict["ml"]["framework"] = ""

    descriptor = Descriptor(descriptor_as_dict, descriptor_config)

    assert not descriptor.framework


def test_framework_explicite(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["ml"]["framework"] = "mxnet"

    descriptor = Descriptor(descriptor_as_dict, descriptor_config)

    assert descriptor.framework == "mxnet"


def test_framework_required(descriptor_as_dict, descriptor_config):
    descriptor_config.valid_frameworks = ["foo"]

    with pytest.raises(DescriptorError):
        Descriptor(descriptor_as_dict, descriptor_config)


def test_framework_invalid(descriptor_as_dict, descriptor_config):
    descriptor_config.valid_frameworks = ["foo"]
    descriptor_as_dict["ml"]["framework"] = "bar"

    with pytest.raises(DescriptorError):
        Descriptor(descriptor_as_dict, descriptor_config)


def test_framework_version(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["ml"]["framework"] = "mxnet"
    descriptor_as_dict["ml"]["framework_version"] = "1.0"

    descriptor = Descriptor(descriptor_as_dict, descriptor_config)

    assert descriptor.framework_version == "1.0"


def test_framework_version_no_framework(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["ml"]["framework"] = ""
    descriptor_as_dict["ml"]["framework_version"] = "1.0"

    with pytest.raises(DescriptorError):
        Descriptor(descriptor_as_dict, descriptor_config)


def test_invalid_strategy(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["hardware"]["strategy"] = "foo"
    with pytest.raises(DescriptorError):
        Descriptor(descriptor_as_dict, descriptor_config)


def test_valid_strategy(descriptor_as_dict, descriptor_config):
    descriptor_as_dict["hardware"]["strategy"] = "horovod"

    descriptor = Descriptor(descriptor_as_dict, descriptor_config)
    assert descriptor.strategy == DistributedStrategy.HOROVOD
