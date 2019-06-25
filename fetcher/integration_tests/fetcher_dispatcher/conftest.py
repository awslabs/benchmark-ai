import kubernetes
from bai_kafka_utils.utils import id_generator
from kazoo.client import KazooClient
from pytest import fixture

from bai_kafka_utils.events import BenchmarkEvent
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from bai_kafka_utils.kafka_service_args import get_kafka_service_config
from fetcher_dispatcher.args import get_fetcher_service_config, FetcherServiceConfig, FetcherJobConfig
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher, create_kubernetes_api_client
from fetcher_dispatcher.kubernetes_tests_client import KubernetesTestUtilsClient


@fixture
def fetcher_service_config() -> FetcherServiceConfig:
    return get_fetcher_service_config(None)


@fixture
def fetcher_job_config(fetcher_service_config: FetcherServiceConfig) -> FetcherJobConfig:
    return fetcher_service_config.fetcher_job


@fixture
def kafka_service_config() -> KafkaServiceConfig:
    kafka_service_config = get_kafka_service_config("FetcherDispatcherIntegrationTest", None)
    return kafka_service_config


@fixture
def zk_client(fetcher_service_config: FetcherServiceConfig):
    return KazooClient(fetcher_service_config.zookeeper_ensemble_hosts)


@fixture
def k8s_dispatcher(fetcher_service_config: FetcherServiceConfig):
    return KubernetesDispatcher(
        fetcher_service_config.kubeconfig,
        fetcher_service_config.zookeeper_ensemble_hosts,
        fetcher_service_config.fetcher_job,
    )


@fixture
def k8s_api_client(fetcher_service_config: FetcherServiceConfig) -> kubernetes.client.ApiClient:
    return create_kubernetes_api_client(fetcher_service_config.kubeconfig)


@fixture
def k8s_test_client(k8s_api_client: kubernetes.client.ApiClient) -> KubernetesTestUtilsClient:
    return KubernetesTestUtilsClient(k8s_api_client)


@fixture
def benchmark_event_dummy_payload(kafka_service_config: KafkaServiceConfig):
    return BenchmarkEvent(
        action_id="ACTION_ID_" + id_generator(),
        message_id="DONTCARE_" + id_generator(),
        client_id="CLIENT_ID_" + id_generator(),
        client_version="DONTCARE",
        client_username="DONTCARE",
        authenticated=False,
        tstamp=42,
        visited=[],
        payload="DONTCARE",
        type=kafka_service_config.consumer_topic,
    )


@fixture
def kafka_consumer_of_produced(kafka_service_config: KafkaServiceConfig):
    print(f"Creating a consumer with {kafka_service_config}...\n")
    kafka_consumer = create_kafka_consumer(
        kafka_service_config.bootstrap_servers,
        kafka_service_config.consumer_group_id,
        # Yes. We consume, what the service has produced
        # All of them!
        [kafka_service_config.producer_topic, kafka_service_config.cmd_return_topic, kafka_service_config.status_topic],
    )
    yield kafka_consumer
    # Unfortunately no __enter__/__exit__ on kafka objects yet - let's do old-school close
    print("Closing consumer...\n")
    kafka_consumer.close()


@fixture
def kafka_producer_to_consume(kafka_service_config: KafkaServiceConfig):
    print("Creating a producer...\n")
    kafka_producer = create_kafka_producer(kafka_service_config.bootstrap_servers)
    yield kafka_producer
    print("Closing producer...\n")
    kafka_producer.close()
