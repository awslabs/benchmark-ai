import os

import kafka
from typing import List, Optional

from bai_common.events import BenchmarkEvent

DEFAULT_ENCODING = os.environ.get("DEFAULT_ENCODING", "utf-8")
BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')


def create_kafka_consumer(topic: str, bootstrap_servers: Optional[List[str]] = BOOTSTRAP_SERVERS,
                          encoding: Optional[str] = DEFAULT_ENCODING) -> kafka.KafkaConsumer:
    def json_deserializer(msg_value):
        return BenchmarkEvent.from_json(msg_value.decode(encoding))

    return kafka.KafkaConsumer(topic, bootstrap_servers=bootstrap_servers, value_deserializer=json_deserializer)


def create_kafka_producer(
        bootstrap_servers: Optional[List[str]] = BOOTSTRAP_SERVERS,
        encoding: Optional[str] = DEFAULT_ENCODING) -> kafka.KafkaProducer:
    def json_serializer(msg_value):
        return msg_value.to_json().encode(encoding)

    return kafka.KafkaProducer(bootstrap_servers=bootstrap_servers, value_serializer=json_serializer)
