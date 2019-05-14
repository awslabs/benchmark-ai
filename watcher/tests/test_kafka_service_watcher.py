import kafka
import pytest

from bai_kafka_utils.kafka_service import KafkaServiceConfig, KafkaService
from bai_watcher.args import WatcherServiceConfig
from bai_watcher.kafka_service_watcher import create_service


@pytest.fixture
def kafka_service_config():
    return KafkaServiceConfig(
        bootstrap_servers=["kafka1:9092", "kafka2:9092"],
        consumer_group_id="GROUP_ID",
        consumer_topic="IN_TOPIC",
        logging_level="DEBUG",
        producer_topic="OUT_TOPIC",
    )


def test_create_service(mocker, kafka_service_config):
    kafka_producer_class = mocker.patch.object(kafka, "KafkaProducer")
    kafka_consumer_class = mocker.patch.object(kafka, "KafkaConsumer")

    service_config = WatcherServiceConfig()
    service = create_service(kafka_service_config, service_config)

    assert isinstance(service, KafkaService)

    kafka_producer_class.assert_called_once()
    kafka_consumer_class.assert_called_once()
