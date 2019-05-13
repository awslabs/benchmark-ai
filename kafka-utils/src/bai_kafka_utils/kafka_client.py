import logging

import kafka
from kafka import KafkaConsumer, KafkaProducer
from typing import List, Type, Tuple

from bai_kafka_utils.events import BenchmarkEvent
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from bai_kafka_utils.utils import DEFAULT_ENCODING

logger = logging.getLogger(__name__)


# Time before a consumer or producer closes if the topics it is subscribed to are idle.
# Setting it to -1 disables the behavior so they never close.
MAX_IDLE_TIME_MS = -1


class WrongBenchmarkEventTypeException(Exception):
    pass


# args from kafka
def create_kafka_consumer_producer(
    kafka_cfg: KafkaServiceConfig, event_type: Type[BenchmarkEvent]
) -> Tuple[KafkaConsumer, KafkaProducer]:
    return (
        create_kafka_consumer(
            kafka_cfg.bootstrap_servers, kafka_cfg.consumer_group_id, kafka_cfg.consumer_topic, event_type
        ),
        create_kafka_producer(kafka_cfg.bootstrap_servers),
    )


def create_kafka_consumer(
    bootstrap_servers: List[str], group_id: str, topic: str, event_type: Type[BenchmarkEvent]
) -> kafka.KafkaConsumer:
    if not issubclass(event_type, BenchmarkEvent):
        raise WrongBenchmarkEventTypeException(f"{str(event_type)} is not a valid benchmark type")

    def json_deserializer(msg_value):
        try:
            return event_type.from_json(msg_value.decode(DEFAULT_ENCODING))
        # Our json deserializer can raise anything - constructor can raise anything).
        # Handling JsonDecodeError and KeyError is not enough
        # For example TypeError is possible as well. So let's play safe.
        except Exception:
            logger.exception("Failed to deserialize %s", msg_value)
            return None

    def key_deserializer(key: bytes):
        try:
            return key.decode(DEFAULT_ENCODING)
        except Exception:
            logger.exception("Failed to deserialize key %s", key)
            return None

    return kafka.KafkaConsumer(
        topic,
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
