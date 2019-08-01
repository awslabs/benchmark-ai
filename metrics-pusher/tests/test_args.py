import pytest
from typing import List

from bai_metrics_pusher.args import get_input, InputValue, create_dict_of_parameter_values_for_callable

ALL_ARGS = f"--pod-namespace pod-namespace --pod-name pod-name"


def test_get_input_with_stdout():
    expected_cfg = InputValue(
        backend="stdout",
        pod_name="pod-name",
        pod_namespace="pod-namespace",
        fifo_filenames=["/tmp/benchmarkai/fifo"],
        backend_args={},
    )
    cfg = get_input(ALL_ARGS + " --backend stdout", environ={})
    assert cfg == expected_cfg


def test_get_input_with_kafka():
    expected_cfg = InputValue(
        backend="kafka",
        pod_name="pod-name",
        fifo_filenames=["/tmp/benchmarkai/fifo"],
        pod_namespace="pod-namespace",
        backend_args={
            "job_id": "123",
            "key": "value",
            "topic": "KAFKA_TOPIC",
            "bootstrap_servers": ["server1:9092", "server2:9092"],
        },
    )
    cfg = get_input(
        ALL_ARGS + " --backend kafka",
        environ={
            "BACKEND_ARG_JOB_ID": "123",
            "BACKEND_ARG_TOPIC": "KAFKA_TOPIC",
            "BACKEND_ARG_KEY": "value",
            "BACKEND_ARG_BOOTSTRAP_SERVERS": "server1:9092,server2:9092",
        },
    )
    assert cfg == expected_cfg


def test_get_input_with_elasticsearch():
    expected_cfg = InputValue(
        backend="elasticsearch",
        pod_name="pod-name",
        pod_namespace="pod-namespace",
        fifo_filenames=["/tmp/benchmarkai/fifo"],
        backend_args={"job_id": "123", "hostname": "es-hostname", "port": 9200},
    )
    cfg = get_input(
        ALL_ARGS + " --backend elasticsearch",
        environ={"BACKEND_ARG_JOB_ID": "123", "BACKEND_ARG_HOSTNAME": "es-hostname", "BACKEND_ARG_PORT": "9200"},
    )
    assert cfg == expected_cfg


def test_get_input_with_multiple_fifo_files(monkeypatch):
    expected_cfg = InputValue(
        backend="stdout",
        pod_name="pod-name",
        pod_namespace="pod-namespace",
        fifo_filenames=["fifo1", "fifo2"],
        backend_args={},
    )
    assert get_input(ALL_ARGS + " --backend stdout --fifo-filenames fifo1 fifo2") == expected_cfg
    monkeypatch.setenv("FIFO_FILENAMES", "fifo1 fifo2")
    assert get_input(ALL_ARGS + " --backend stdout") == expected_cfg


def test_method_receiving_extra_parameter():
    def method(a: str):
        pass

    with pytest.raises(KeyError):
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_parameter": "1"}, method)


def test_method_receiving_less_parameters():
    def method(a: str):
        pass

    with pytest.raises(ValueError):
        create_dict_of_parameter_values_for_callable("prefix_", {"other-item": "foo"}, method)


def test_method_receiving_parameter_without_annotation():
    def method(a):
        pass

    with pytest.raises(AssertionError):
        create_dict_of_parameter_values_for_callable("prefix_", {}, method)


def test_method_receiving_str():
    def method_str(a: str):
        pass

    assert create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "1"}, method_str) == {"a": "1"}


def test_method_receiving_int():
    def method_int(a: float):
        pass

    assert create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "1"}, method_int) == {"a": 1}


def test_method_receiving_list_of_str():
    def method_with_list_of_str(a: List[str]):
        pass

    assert create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "v0"}, method_with_list_of_str) == {
        "a": ["v0"]
    }
    assert create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "v0,v1"}, method_with_list_of_str) == {
        "a": ["v0", "v1"]
    }


def test_method_receiving_list_of_int():
    def method_with_list_of_int(a: List[int]):
        pass

    expected = {"a": [1, 2]}
    assert (
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "1,2"}, method_with_list_of_int)
        == expected
    )
    assert (
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "1, 2"}, method_with_list_of_int)
        == expected
    )
    assert (
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": " 1, 2"}, method_with_list_of_int)
        == expected
    )
    assert (
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": " 1, 2 "}, method_with_list_of_int)
        == expected
    )


def test_method_receiving_2_arguments():
    def method_with_2_arguments(a: str, b: str):
        pass

    assert create_dict_of_parameter_values_for_callable(
        "prefix_", {"prefix_a": "a", "prefix_b": "b"}, method_with_2_arguments
    ) == {"a": "a", "b": "b"}
