from kazoo.client import KazooClient
from pytest import fixture

from bai_kafka_utils.events import BenchmarkEvent
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from bai_kafka_utils.kafka_service_args import get_kafka_service_config
from fetcher_dispatcher.args import get_fetcher_service_config, FetcherServiceConfig
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher


@fixture
def fetcher_service_config() -> FetcherServiceConfig:
    return get_fetcher_service_config(None)


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
def benchmark_event_dummy_payload():
    return BenchmarkEvent(
        action_id="ACTION_ID",
        message_id="DONTCARE",
        client_id="CLIENT_ID",
        client_version="DONTCARE",
        client_username="DONTCARE",
        authenticated=False,
        tstamp=42,
        visited=[],
        payload="DONTCARE",
        type="DONTCARE",
    )


@fixture
def kafka_consumer_of_produced(kafka_service_config: KafkaServiceConfig):
    print(f"Creating a consumer with {kafka_service_config}...\n")
    kafka_consumer = create_kafka_consumer(
        kafka_service_config.bootstrap_servers,
        kafka_service_config.consumer_group_id,
        # Yes. We consume, what the service has produced
        [kafka_service_config.producer_topic],
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
