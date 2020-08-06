import pytest

from bai_kafka_utils.executors.descriptor import (
    DescriptorError,
    ONE_PER_GPU,
    DistributedStrategy,
    BenchmarkDescriptor,
    MLFramework,
)


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
        "cs_missing_server_model_path_descriptor.toml",
        "cs_missing_server_model_src_descriptor.toml",
        "cs_missing_server_output_metrics_descriptor.toml",
        "cs_missing_server_output_metric_name_descriptor.toml",
        "cs_missing_server_output_metric_units_descriptor.toml",
        "cs_missing_server_output_metric_pattern_descriptor.toml",
        "cs_missing_readiness_probe_path.toml",
    ],
)
def test_wrong_descriptor(datadir, filename):
    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_toml(str(datadir / filename))


@pytest.mark.parametrize(
    "filename",
    [
        "minimal_descriptor.toml",
        "cs_hyperparameter_descriptor.toml",
        "cs_minimal_descriptor.toml",
        "cs_with_optionals_descriptor.toml",
        "cs_minimal_with_models_descriptor.toml",
    ],
)
def test_minimal_descriptor(datadir, filename):
    BenchmarkDescriptor.from_toml(str(datadir / filename))


@pytest.mark.parametrize("filename", ["cs_hyperparameter_descriptor.toml"])
def test_hyper_params_job_name(datadir, filename):
    descriptor = BenchmarkDescriptor.from_toml(str(datadir / filename))
    assert descriptor.custom_params.hyper_params["amp"] == "True"
    assert descriptor.custom_params.hyper_params["validation_frequency"] == 10
    assert descriptor.custom_params.python_version == "py2"


@pytest.mark.parametrize("scheduling", ["0 0 0 0", "* * ? * *", "single"])
def test_invalid_scheduling(descriptor_as_adict, scheduling):
    descriptor_as_adict.info.scheduling = scheduling
    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())


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
def test_invalid_custom_labels(descriptor_as_adict, labels):
    descriptor_as_adict.info.labels = labels
    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())


def test_invalid_args_type(descriptor_as_adict):
    descriptor_as_adict.ml.args = 4
    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())


def test_distributed_explicit(descriptor_as_adict):
    descriptor_as_adict.hardware.distributed.processes_per_instance = "4"
    descriptor = BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())

    assert descriptor.hardware.processes_per_instance == 4


def test_distributed_default(descriptor_as_adict):
    descriptor = BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())

    assert descriptor.hardware.processes_per_instance == 1


def test_distributed_gpus(descriptor_as_adict):
    descriptor_as_adict.hardware.instance_type = "p3.8xlarge"
    descriptor_as_adict.hardware.distributed.processes_per_instance = ONE_PER_GPU
    descriptor = BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())

    assert descriptor.hardware.processes_per_instance == 4


def test_distributed_gpus_on_cpu(descriptor_as_adict):
    descriptor_as_adict.hardware.instance_type = "t2.small"
    descriptor_as_adict.hardware.distributed.processes_per_instance = ONE_PER_GPU

    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())


def test_distributed_num_instances_str(descriptor_as_adict):
    descriptor_as_adict.hardware.distributed.num_instances = 4
    descriptor = BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())

    assert descriptor.hardware.distributed.num_instances == 4


def test_distributed_num_instances_default(descriptor_as_adict):
    descriptor = BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())

    assert descriptor.hardware.distributed.num_instances == 2


def test_framework_explicit(descriptor_as_adict):
    descriptor_as_adict.ml.framework = "mxnet"

    descriptor = BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())

    assert descriptor.ml.framework == MLFramework.MXNET


def test_framework_required(descriptor_as_adict, descriptor_config):
    descriptor_config.valid_frameworks = ["foo"]

    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict(), descriptor_config)


@pytest.mark.parametrize("script_value", ["", "_invalid"])
def test_script_file_required(descriptor_as_adict, script_value):
    descriptor_as_adict.ml.script.script = script_value

    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())


def test_framework_invalid(descriptor_as_adict, descriptor_config):
    descriptor_config.valid_frameworks = ["foo"]
    descriptor_as_adict.ml.framework = "bar"

    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict(), descriptor_config)


def test_framework_version(descriptor_as_adict):
    descriptor_as_adict.ml.framework = "mxnet"
    descriptor_as_adict.ml.framework_version = "1.0"

    descriptor = BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())

    assert descriptor.ml.framework_version == "1.0"


def test_framework_version_no_framework(descriptor_as_adict):
    descriptor_as_adict.ml.framework = ""
    descriptor_as_adict.ml.framework_version = "1.0"

    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())


def test_invalid_strategy(descriptor_as_adict):
    descriptor_as_adict.hardware.strategy = "foo"
    with pytest.raises(DescriptorError):
        BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())


def test_valid_strategy(descriptor_as_adict):
    descriptor_as_adict.hardware.strategy = "horovod"

    descriptor = BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict())
    assert descriptor.hardware.strategy == DistributedStrategy.HOROVOD
