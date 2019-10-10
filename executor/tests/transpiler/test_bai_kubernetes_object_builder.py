import base64
import json
import random
from unittest.mock import create_autospec

import pytest
from pytest import fixture

from bai_kafka_utils.executors.descriptor import BenchmarkDescriptor, DescriptorError
from transpiler.bai_knowledge import (
    BaiKubernetesObjectBuilder,
    SingleRunBenchmarkKubernetesObjectBuilder,
    create_single_run_benchmark_bai_k8s_builder,
)
from transpiler.config import EnvironmentInfo

WHITELISTED_ZONE = "us-east-1a"

INVALID_ZONE = "us-east-1w"

INVALID_ZONE_ID = "use1-az42"

WHITELISTED_ZONE_ID = "use1-az1"

JOB_ID = "JOB_ID"


def test_add_container_cmd(descriptor, bai_config, fetched_data_sources, bai_environment_info, benchmark_event):
    descriptor.ml.benchmark_code = "cmd"
    descriptor.ml.args = "arg1 arg2"

    bai_k8s_builder = create_single_run_benchmark_bai_k8s_builder(
        descriptor,
        bai_config,
        fetched_data_sources,
        [],
        JOB_ID,
        environment_info=bai_environment_info,
        event=benchmark_event,
    )
    container = bai_k8s_builder.root.find_container("benchmark")
    assert container.command == ["cmd", "arg1", "arg2"]
    assert "args" not in container


def test_add_container_no_cmd(descriptor, bai_config, fetched_data_sources, bai_environment_info, benchmark_event):
    descriptor.ml.benchmark_code = ""
    descriptor.ml.args = "arg1 arg2=abc"

    bai_k8s_builder = create_single_run_benchmark_bai_k8s_builder(
        descriptor,
        bai_config,
        fetched_data_sources,
        [],
        JOB_ID,
        environment_info=bai_environment_info,
        event=benchmark_event,
    )
    container = bai_k8s_builder.root.find_container("benchmark")
    assert "command" not in container
    assert container.args == ["arg1", "arg2=abc"]


def test_choose_zone_passed(descriptor: BenchmarkDescriptor, bai_environment_info: EnvironmentInfo):
    descriptor.hardware.availability_zone = WHITELISTED_ZONE

    assert WHITELISTED_ZONE == SingleRunBenchmarkKubernetesObjectBuilder.choose_availability_zone(
        descriptor, bai_environment_info
    )


def test_choose_zone_id(descriptor: BenchmarkDescriptor, bai_environment_info: EnvironmentInfo):
    descriptor.hardware.aws_zone_id = WHITELISTED_ZONE_ID

    assert WHITELISTED_ZONE == SingleRunBenchmarkKubernetesObjectBuilder.choose_availability_zone(
        descriptor, bai_environment_info
    )


def test_choose_zone_rnd(
    descriptor: BenchmarkDescriptor, bai_environment_info: EnvironmentInfo, mock_random: random.Random
):
    descriptor.zone_id = None

    assert WHITELISTED_ZONE == SingleRunBenchmarkKubernetesObjectBuilder.choose_availability_zone(
        descriptor, bai_environment_info, mock_random
    )


def test_choose_zone_invalid(
    descriptor: BenchmarkDescriptor, bai_environment_info: EnvironmentInfo, mock_random: random.Random
):
    descriptor.hardware.availability_zone = INVALID_ZONE

    with pytest.raises(DescriptorError):
        SingleRunBenchmarkKubernetesObjectBuilder.choose_availability_zone(
            descriptor, bai_environment_info, mock_random
        )


def test_choose_zone_id_invalid(
    descriptor: BenchmarkDescriptor, bai_environment_info: EnvironmentInfo, mock_random: random.Random
):
    descriptor.hardware.aws_zone_id = INVALID_ZONE_ID

    with pytest.raises(DescriptorError):
        SingleRunBenchmarkKubernetesObjectBuilder.choose_availability_zone(
            descriptor, bai_environment_info, mock_random
        )


def test_metrics(descriptor):
    metrics = BaiKubernetesObjectBuilder.get_metrics_from_descriptor(descriptor)
    assert metrics is not None
    json_object = json.loads(metrics)
    assert len(json_object) == 2
    m = json_object[0]
    assert m["name"] == "accuracy"
    assert base64.b64decode(m["pattern"]).decode("utf-8") == "accuracy=([-+]?\\d*\\.\\d+|\\d+)"
    m = json_object[1]
    assert m["name"] == "throughput"
    assert base64.b64decode(m["pattern"]).decode("utf-8") == "throughput=([-+]?\\d*\\.\\d+|\\d+)"


@fixture
def mock_random() -> random.Random:
    def return_first(passed_list):
        return passed_list[0]

    mock = create_autospec(random.Random)
    mock.choice.side_effect = return_first
    return mock
