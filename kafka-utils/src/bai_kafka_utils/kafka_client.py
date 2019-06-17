import logging

import kafka
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from typing import List, Tuple

from kafka.errors import TopicAlreadyExistsError

from bai_kafka_utils.events import BenchmarkEvent, get_topic_event_type
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from bai_kafka_utils.utils import DEFAULT_ENCODING

logger = logging.getLogger(__name__)


# Time before a consumer or producer closes if the topics it is subscribed to are idle.
# Setting to a really high number (3 years) because we don't want it to ever close.
MAX_IDLE_TIME_MS = 100000000000

# TODO: take num_partitions and replication_factor from terraform output instead of hardcoding them
NUM_PARTITIONS = 3
REPLICATION_FACTOR = 3


class WrongBenchmarkEventTypeException(Exception):
    pass


# args from kafka
def create_kafka_consumer_producer(
    kafka_cfg: KafkaServiceConfig, service_name: str
) -> Tuple[KafkaConsumer, KafkaProducer]:
    # Each service's Kafka consumer subscribes to both the service's input topic and the cmd_submit topic
    consumer_topics = [kafka_cfg.consumer_topic, kafka_cfg.cmd_submit_topic]

    required_topics = [kafka_cfg.producer_topic]
    create_kafka_topics(required_topics, kafka_cfg.bootstrap_servers, service_name)

    return (
        create_kafka_consumer(kafka_cfg.bootstrap_servers, kafka_cfg.consumer_group_id, consumer_topics),
        create_kafka_producer(kafka_cfg.bootstrap_servers),
    )


def create_kafka_consumer(bootstrap_servers: List[str], group_id: str, topics: List[str]) -> kafka.KafkaConsumer:
    def json_deserializer(msg_value):
        try:
            envelope = BenchmarkEvent.from_json(msg_value.decode(DEFAULT_ENCODING))
            event_type = get_topic_event_type(envelope.type)
            return event_type.from_json(msg_value.decode(DEFAULT_ENCODING))
        # Our json deserializer can raise anything - constructor can raise anything).
        # Handling JsonDecodeError and KeyError is not enough
        # For example TypeError is possible as well. So let's play safe.
        except Exception:
            logger.exception("Failed to deserialize %s", msg_value)
            return None

    # key can be None
    def key_deserializer(key: bytes):
        try:
            return key.decode(DEFAULT_ENCODING) if key is not None else None
        except UnicodeDecodeError:
            logger.exception("Failed to deserialize key %s", key)
            return None

    return kafka.KafkaConsumer(
        *topics,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        value_deserializer=json_deserializer,
        key_deserializer=key_deserializer,
        connections_max_idle_ms=MAX_IDLE_TIME_MS,
    )


def create_kafka_producer(bootstrap_servers: List[str]) -> kafka.KafkaProducer:
    def json_serializer(msg_value):
        return msg_value.to_json().encode(DEFAULT_ENCODING)

    def key_serializer(key: str):
        return key.encode(DEFAULT_ENCODING)

    return kafka.KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=json_serializer,
        connections_max_idle_ms=MAX_IDLE_TIME_MS,
        key_serializer=key_serializer,
    )


def create_kafka_topics(
    new_topics: List[str],
    bootstrap_servers: List[str],
    service_name: str,
    num_partitions: int = NUM_PARTITIONS,
    replication_factor: int = REPLICATION_FACTOR,
):
    admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers, client_id=service_name)

    new_topic_list = [
        NewTopic(name=topic, num_partitions=num_partitions, replication_factor=replication_factor)
        for topic in new_topics
    ]

    for topic in new_topic_list:
        try:
            admin_client.create_topics(new_topics=[topic])
            logger.info(f"Created kafka topic {topic}")
        except TopicAlreadyExistsError:
            logger.warning(f"Error creating topic {topic}, it already exists")
