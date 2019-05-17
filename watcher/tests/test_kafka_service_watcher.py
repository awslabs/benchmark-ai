from unittest.mock import call

import kafka
import pytest

from bai_kafka_utils.kafka_service import KafkaServiceConfig, KafkaService
from bai_watcher.args import WatcherServiceConfig
from bai_watcher.kafka_service_watcher import create_service, WatchJobsEventHandler


@pytest.fixture
def kafka_service_config():
    return KafkaServiceConfig(
        bootstrap_servers=["kafka1:9092", "kafka2:9092"],
        consumer_group_id="GROUP_ID",
        consumer_topic="IN_TOPIC",
        logging_level="DEBUG",
        producer_topic="OUT_TOPIC",
    )


@pytest.fixture(autouse=True)
def kubernetes_config(mocker):
    return mocker.patch("kubernetes.config")


def test_create_service(mocker, kafka_service_config):
    kafka_producer_class = mocker.patch.object(kafka, "KafkaProducer")
    kafka_consumer_class = mocker.patch.object(kafka, "KafkaConsumer")

    service_config = WatcherServiceConfig()
    service = create_service(kafka_service_config, service_config)

    assert isinstance(service, KafkaService)

    kafka_producer_class.assert_called_once()
    kafka_consumer_class.assert_called_once()


def test_constructor_loads_kubernetes_config_with_inexistent_kubeconfig_file(kubernetes_config):
    service_config = WatcherServiceConfig(kubeconfig="inexistent-path")
    WatchJobsEventHandler(service_config)
    assert kubernetes_config.load_incluster_config.call_args_list == [call()]
    assert kubernetes_config.load_kube_config.call_args_list == []


def test_constructor_loads_kubernetes_config_with_existing_kubeconfig_file(kubernetes_config, datadir):
    kubeconfig_filename = str(datadir / "kubeconfig")
    service_config = WatcherServiceConfig(kubeconfig=kubeconfig_filename)
    WatchJobsEventHandler(service_config)
    assert kubernetes_config.load_incluster_config.call_args_list == []
    assert kubernetes_config.load_kube_config.call_args_list == [call(kubeconfig_filename)]
