import os

import pytest
from pytest import fixture
from time import time
from typing import Callable

from bai_kafka_utils.events import FetcherPayload, BenchmarkDoc, BenchmarkEvent, DataSet
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceConfig

TIMEOUT_FOR_DOWNLOAD_SEC = 5 * 60

kafka_cfg = KafkaServiceConfig(
    consumer_group_id=os.environ.get("CONSUMER_GROUP_ID"),
    producer_topic=os.environ.get("CONSUMER_TOPIC"),
    consumer_topic=os.environ.get("PRODUCER_TOPIC"),
    bootstrap_servers=os.environ.get("BOOTSTRAP_SERVERS"),
    logging_level="INFO"
)

consumer, producer = create_kafka_consumer_producer(kafka_cfg, FetcherPayload)

# Should be successful in any environment
SOME_EXISTING_DATASET = "http://files.grouplens.org/datasets/movielens/ml-1m.zip"


@fixture
def benchmark_event():
    doc = BenchmarkDoc({"var": "val"}, "var = val", "")
    cur_time = time()
    payload = FetcherPayload(toml=doc, data_sets=[DataSet(src=f"{SOME_EXISTING_DATASET}?time={cur_time}")])
    return BenchmarkEvent(request_id="REQUEST_ID", message_id="MESSAGE_ID", client_id="CLIENT_ID",
                          client_version="CLIENT_VERSION", client_user="CLIENT_USER", authenticated=False,
                          date=42, visited=[],
                          payload=payload)


def get_message_is_the_response(src_event: BenchmarkEvent) -> Callable[[BenchmarkEvent], bool]:
    src_to_check = src_event.payload.data_sets[0].src

    def filter_event(event: BenchmarkEvent) -> bool:
        return isinstance(event.payload, FetcherPayload) and \
               any(data_set.src == src_to_check and data_set.dst for data_set in event.payload.data_sets)

    return filter_event


POLL_TIMEOUT_MS = 500


@pytest.mark.timeout(TIMEOUT_FOR_DOWNLOAD_SEC)
def test_producer(benchmark_event: BenchmarkEvent):
    producer.send(kafka_cfg.producer_topic, benchmark_event)

    filter_event = get_message_is_the_response(benchmark_event)

    while True:
        records = consumer.poll(POLL_TIMEOUT_MS)
        for topic, recs in records.items():
            for msg in recs:
                if filter_event(msg.value):
                    return
