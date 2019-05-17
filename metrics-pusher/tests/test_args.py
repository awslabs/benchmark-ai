import pytest
from typing import List

from bai_metrics_pusher.args import get_input, InputValue, create_dict_of_parameter_values_for_callable

ALL_ARGS = f"--pod-namespace pod-namespace --pod-name pod-name "


def test_get_input():
    expected_cfg = InputValue(backend="stdout", pod_name="pod-name", pod_namespace="pod-namespace", backend_args={})
    cfg = get_input(ALL_ARGS + " --backend stdout")
    assert cfg == expected_cfg


def test_get_input_with_stdout():
    expected_cfg = InputValue(backend="stdout", pod_name="pod-name", pod_namespace="pod-namespace", backend_args={})
    cfg = get_input("--backend stdout --pod-namespace pod-namespace --pod-name pod-name ", environ={})
    assert cfg == expected_cfg


def test_get_input_with_kafka():
    expected_cfg = InputValue(
        backend="kafka",
        pod_name="pod-name",
        pod_namespace="pod-namespace",
        backend_args={"key": "value", "topic": "KAFKA_TOPIC", "bootstrap_servers": ["server1:9092", "server2:9092"]},
    )
    cfg = get_input(
        ALL_ARGS + " --backend kafka",
        environ={
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
        backend_args={"hostname": "es-hostname", "port": 9200},
    )
    cfg = get_input(
        ALL_ARGS + " --backend elasticsearch",
        environ={"BACKEND_ARG_HOSTNAME": "es-hostname", "BACKEND_ARG_PORT": "9200"},
    )
    assert cfg == expected_cfg


def test_factory_method_with_extra_parameter():
    def factory_method_str(a: str):
        pass

    with pytest.raises(KeyError):
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_parameter": "1"}, factory_method_str)


def test_factory_method_str():
    def factory_method_str(a: str):
        pass

    assert create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "1"}, factory_method_str) == {"a": "1"}


def test_factory_method_int():
    def factory_method_int(a: float):
        pass

    assert create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "1"}, factory_method_int) == {"a": 1}


def test_factory_method_with_list_of_str():
    def factory_method_with_list_of_str(a: List[str]):
        pass

    assert create_dict_of_parameter_values_for_callable(
        "prefix_", {"prefix_a": "v0"}, factory_method_with_list_of_str
    ) == {"a": ["v0"]}
    assert create_dict_of_parameter_values_for_callable(
        "prefix_", {"prefix_a": "v0,v1"}, factory_method_with_list_of_str
    ) == {"a": ["v0", "v1"]}


def test_factory_method_with_list_of_int():
    def factory_method_with_list_of_int(a: List[int]):
        pass

    expected = {"a": [1, 2]}
    assert (
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "1,2"}, factory_method_with_list_of_int)
        == expected
    )
    assert (
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": "1, 2"}, factory_method_with_list_of_int)
        == expected
    )
    assert (
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": " 1, 2"}, factory_method_with_list_of_int)
        == expected
    )
    assert (
        create_dict_of_parameter_values_for_callable("prefix_", {"prefix_a": " 1, 2 "}, factory_method_with_list_of_int)
        == expected
    )


def test_factory_method_with_2_arguments():
    def factory_method_with_2_arguments(a: str, b: str):
        pass

    assert create_dict_of_parameter_values_for_callable(
        "prefix_", {"prefix_a": "a", "prefix_b": "b"}, factory_method_with_2_arguments
    ) == {"a": "a", "b": "b"}
