from random import randint

from kazoo.client import KazooClient
from pytest import fixture

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
    # Salt the consumer_group_id
    kafka_service_config.consumer_group_id += str(randint(0, 100000))
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
