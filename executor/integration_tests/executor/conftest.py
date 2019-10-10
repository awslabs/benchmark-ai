import kubernetes
import toml
from typing import Dict, Any
from bai_k8s_utils.kubernetes_tests_client import KubernetesTestUtilsClient
from bai_kafka_utils.events import (
    BenchmarkEvent,
    FetcherBenchmarkEvent,
    BenchmarkDoc,
    FetcherPayload,
    create_from_object,
)
from pytest import fixture

from bai_kafka_utils.integration_tests.fixtures import (
    kafka_service_config,
    kafka_consumer_of_produced,
    kafka_prepolled_consumer_of_produced,
    kafka_producer_to_consume,
    benchmark_event_dummy_payload,
)

from executor import SERVICE_NAME


def shut_up_unused_kafka():
    kafka_service_config, kafka_consumer_of_produced, kafka_producer_to_consume, benchmark_event_dummy_payload
    kafka_prepolled_consumer_of_produced


def create_fetcher_benchmark_event_from_dict(
    benchmark_event_dummy_payload: BenchmarkEvent, toml_dict: Dict[str, Any]
) -> FetcherBenchmarkEvent:
    doc = BenchmarkDoc(toml_dict, "var = val", "")  # We don't care about the initial TOML
    fetch_payload = FetcherPayload(toml=doc, datasets=[])
    return create_from_object(
        FetcherBenchmarkEvent,
        benchmark_event_dummy_payload,
        payload=fetch_payload,
        action_id=benchmark_event_dummy_payload.action_id.replace("_", "-"),
    )


@fixture
def k8s_test_client(k8s_api_client: kubernetes.client.ApiClient) -> KubernetesTestUtilsClient:
    return KubernetesTestUtilsClient(k8s_api_client, SERVICE_NAME)


@fixture
def k8s_api_client() -> kubernetes.client.ApiClient:
    kubernetes.config.load_incluster_config()

    configuration = kubernetes.client.Configuration()
    return kubernetes.client.ApiClient(configuration)


@fixture
def fetcher_inference_benchmark_event(
    benchmark_event_dummy_payload: BenchmarkEvent, shared_datadir
) -> FetcherBenchmarkEvent:
    toml_dict = toml.load(str(shared_datadir / "inference_benchmark.toml"))
    return create_fetcher_benchmark_event_from_dict(benchmark_event_dummy_payload, toml_dict)


@fixture
def fetcher_benchmark_event(benchmark_event_dummy_payload: BenchmarkEvent) -> FetcherBenchmarkEvent:
    toml_dict = {
        "spec_version": "0.1.0",
        "ml": {"benchmark_code": "echo hello world"},
        "info": {"description": "something", "task_name": "test-2"},
        "hardware": {"instance_type": "local", "strategy": "single_node"},
        "env": {"docker_image": "alpine", "vars": {"FOO": "BAR", "IVAL": 42}},
    }
    return create_fetcher_benchmark_event_from_dict(benchmark_event_dummy_payload, toml_dict)
