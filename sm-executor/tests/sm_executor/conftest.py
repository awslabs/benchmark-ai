import addict

from bai_kafka_utils.executors.descriptor import DescriptorConfig, BenchmarkDescriptor
from pytest import fixture


from sm_executor.args import SageMakerExecutorConfig
from sm_executor.frameworks import TENSORFLOW_FRAMEWORK, MXNET_FRAMEWORK


@fixture
def descriptor_config() -> DescriptorConfig:
    return DescriptorConfig(
        valid_strategies=["single_node", "horovod"], valid_frameworks=[TENSORFLOW_FRAMEWORK, MXNET_FRAMEWORK]
    )


@fixture
def sagemaker_config(descriptor_config) -> SageMakerExecutorConfig:
    return SageMakerExecutorConfig(
        subnets=["subnet-1", "subnet-2"],
        security_group_ids=["sg-1"],
        s3_nodata="s3://somebucket/nodata",
        s3_output_bucket="output-bucket",
        sm_role="some_role",
        tmp_sources_dir="/tmp/dir",
        descriptor_config=descriptor_config,
    )


@fixture
def descriptor_as_adict(descriptor_config):
    return addict.Dict(
        spec_version="0.1.0",
        info=addict.Dict(description="something"),
        hardware=addict.Dict(instance_type="p3.8xlarge", strategy="single_node"),
        env=addict.Dict(docker_image="jlcont/benchmarking:270219"),
        ml=addict.Dict(
            benchmark_code="python /home/benchmark/image_classification.py",
            framework="tensorflow",
            framework_version="1.12",
        ),
        data=addict.Dict(sources=[addict.Dict(src="foo1", path="bar1"), addict.Dict(src="foo2", path="bar2")]),
    )


@fixture
def descriptor(descriptor_config, descriptor_as_adict):
    return BenchmarkDescriptor.from_dict(descriptor_as_adict.to_dict(), descriptor_config)


@fixture
def descriptor_customparams_as_adict(descriptor_config):
    return addict.Dict(
        spec_version="0.1.0",
        info=addict.Dict(description="something", labels={"task_name": "exampleTask", "batch_size": "64"}),
        hardware=addict.Dict(instance_type="p3.8xlarge", strategy="single_node"),
        env=addict.Dict(docker_image="jlcont/benchmarking:270219"),
        ml=addict.Dict(
            benchmark_code="python /home/benchmark/image_classification.py",
            framework="tensorflow",
            framework_version="1.12",
        ),
        custom_params=addict.Dict(
            sagemaker_job_name="testJob",
            merge=True,
            hyper_params={"validiation_frequency": 10, "amp": True, "weight": 0.1},
            metric_definitions=[{"Name": "img_sec", "Regex": r"[d*\.?\d]+"}],
        ),
        data=addict.Dict(sources=[addict.Dict(src="foo1", path="bar1"), addict.Dict(src="foo2", path="bar2")]),
    )


@fixture
def customparams_descriptor(descriptor_config, descriptor_customparams_as_adict):
    return BenchmarkDescriptor.from_dict(descriptor_customparams_as_adict.to_dict(), descriptor_config)


@fixture
def sagemaker_final_metric_data_list():
    return [
        {"MetricName": "iter", "Value": 51.900001525878906, "Timestamp": "1970-01-19T03:48:31.114000-08:00"},
        {"MetricName": "img_sec", "Value": 51.900001525878906, "Timestamp": "1970-01-19T03:48:31.114000-08:00"},
    ]
