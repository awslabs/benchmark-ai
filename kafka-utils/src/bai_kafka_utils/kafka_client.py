import logging

import kafka
from typing import List

from bai_kafka_utils.events import BenchmarkEvent
from bai_kafka_utils.utils import DEFAULT_ENCODING

logger = logging.getLogger(__name__)


def create_kafka_consumer(bootstrap_servers: List[str], group_id: str, topic: str) -> kafka.KafkaConsumer:
    def json_deserializer(msg_value):
        try:
            return BenchmarkEvent.from_json(msg_value.decode(DEFAULT_ENCODING))
        except:
            logger.exception("Failed to deserialized %s", msg_value)
            return None

    return kafka.KafkaConsumer(topic, bootstrap_servers=bootstrap_servers, group_id=group_id,
                               value_deserializer=json_deserializer)


def create_kafka_producer(
        bootstrap_servers: List[str]) -> kafka.KafkaProducer:
    def json_serializer(msg_value):
        return msg_value.to_json().encode(DEFAULT_ENCODING)

    return kafka.KafkaProducer(bootstrap_servers=bootstrap_servers, value_serializer=json_serializer)
