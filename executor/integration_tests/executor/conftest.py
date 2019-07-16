import kubernetes
from bai_k8s_utils.kubernetes_tests_client import KubernetesTestUtilsClient
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


@fixture
def k8s_test_client(k8s_api_client: kubernetes.client.ApiClient) -> KubernetesTestUtilsClient:
    return KubernetesTestUtilsClient(k8s_api_client, SERVICE_NAME)


@fixture
def k8s_api_client() -> kubernetes.client.ApiClient:
    kubernetes.config.load_incluster_config()

    configuration = kubernetes.client.Configuration()
    return kubernetes.client.ApiClient(configuration)
