from kafka import KafkaConsumer
from pytest import fixture

from bai_kafka_utils.events import BenchmarkEvent
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from bai_kafka_utils.kafka_service_args import get_kafka_service_config
from bai_kafka_utils.utils import id_generator

PREPOLL_TIMEOUT_MS = 10000


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
def kafka_prepolled_consumer_of_produced(kafka_consumer_of_produced: KafkaConsumer):
    print("Waiting a bit for consumer group to settle")
    kafka_consumer_of_produced.poll(PREPOLL_TIMEOUT_MS)
    return kafka_consumer_of_produced


@fixture
def kafka_producer_to_consume(kafka_service_config: KafkaServiceConfig):
    print("Creating a producer...\n")
    kafka_producer = create_kafka_producer(kafka_service_config.bootstrap_servers)
    yield kafka_producer
    print("Closing producer...\n")
    kafka_producer.close()


@fixture
def kafka_service_config() -> KafkaServiceConfig:
    kafka_service_config = get_kafka_service_config("IntegrationTest", None)
    return kafka_service_config


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
