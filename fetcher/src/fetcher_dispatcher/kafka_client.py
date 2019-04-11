import os

import kafka

from fetcher_dispatcher.events.benchmark_event import BenchmarkEvent

DEFAULT_ENCODING = os.environ.get("DEFAULT_ENCODING", "utf-8")
BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')


def kafka_consumer(topic: str):
    def json_deserializer(m):
        return BenchmarkEvent.from_json(m.decode(DEFAULT_ENCODING))

    return kafka.KafkaConsumer(topic, bootstrap_servers=BOOTSTRAP_SERVERS, value_deserializer=json_deserializer)


def kafka_producer():
    def json_serializer(m):
        return m.to_json().encode(DEFAULT_ENCODING)

    return kafka.KafkaProducer(bootstrap_servers=BOOTSTRAP_SERVERS, value_serializer=json_serializer)
