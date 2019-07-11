import kubernetes
from kazoo.client import KazooClient
from pytest import fixture

from bai_kafka_utils.integration_tests.fixtures import (
    kafka_service_config,
    kafka_consumer_of_produced,
    kafka_producer_to_consume,
    benchmark_event_dummy_payload,
)


from fetcher_dispatcher import SERVICE_NAME
from fetcher_dispatcher.args import get_fetcher_service_config, FetcherServiceConfig, FetcherJobConfig
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher, create_kubernetes_api_client
from bai_k8s_utils.kubernetes_tests_client import KubernetesTestUtilsClient


@fixture
def fetcher_service_config() -> FetcherServiceConfig:
    return get_fetcher_service_config(None)


@fixture
def fetcher_job_config(fetcher_service_config: FetcherServiceConfig) -> FetcherJobConfig:
    return fetcher_service_config.fetcher_job


@fixture
def zk_client(fetcher_service_config: FetcherServiceConfig):
    return KazooClient(fetcher_service_config.zookeeper_ensemble_hosts)


@fixture
def k8s_dispatcher(fetcher_service_config: FetcherServiceConfig):
    return KubernetesDispatcher(
        SERVICE_NAME,
        fetcher_service_config.kubeconfig,
        fetcher_service_config.zookeeper_ensemble_hosts,
        fetcher_service_config.fetcher_job,
    )


@fixture
def k8s_api_client(fetcher_service_config: FetcherServiceConfig) -> kubernetes.client.ApiClient:
    return create_kubernetes_api_client(fetcher_service_config.kubeconfig)


@fixture
def k8s_test_client(k8s_api_client: kubernetes.client.ApiClient) -> KubernetesTestUtilsClient:
    return KubernetesTestUtilsClient(k8s_api_client, SERVICE_NAME)


def shut_up_unused_kafka():
    kafka_service_config, kafka_consumer_of_produced, kafka_producer_to_consume, benchmark_event_dummy_payload
