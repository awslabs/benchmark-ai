import dataclasses

import pytest
from kafka import KafkaConsumer, KafkaProducer
from time import time
from typing import Callable

from bai_kafka_utils.events import FetcherPayload, BenchmarkDoc, BenchmarkEvent, DataSet, FetchedType, FetcherStatus
from bai_kafka_utils.kafka_service import KafkaServiceConfig

# Should be successful in any environment - has delay of 10s for consumer group to setup
EXISTING_DATASET_WITH_DELAY = "http://files.grouplens.org/datasets/movielens/ml-1m.zip?delay"

# Should fail in any environment - has delay of 10s for consumer group to setup
FAILING_DATASET_WITH_DELAY = "http://files.grouplens.org/datasets/movielens/fail.zip?delay"


def get_salted_src(src: str) -> str:
    cur_time = time()
    return f"{src}?time={cur_time}"


def get_fetcher_benchmark_event(template_event: BenchmarkEvent, src: str):
    doc = BenchmarkDoc({"var": "val"}, "var = val", "")
    fetch_payload = FetcherPayload(toml=doc, datasets=[DataSet(src=get_salted_src(src))])
    return dataclasses.replace(template_event, payload=fetch_payload)


def successful_dataset(data_set: DataSet) -> bool:
    return data_set.dst is not None and data_set.type == FetchedType.FILE and data_set.status == FetcherStatus.DONE


def failed_dataset(data_set: DataSet) -> bool:
    return data_set.dst is None and data_set.message is not None and data_set.status == FetcherStatus.FAILED


def get_message_is_the_response(
    src_event: BenchmarkEvent, data_set_check: Callable[[DataSet], bool]
) -> Callable[[BenchmarkEvent], bool]:
    src_to_check = src_event.payload.datasets[0].src

    def filter_event(event: BenchmarkEvent) -> bool:
        print(f"Got evt {event}")

        return isinstance(event.payload, FetcherPayload) and any(
            data_set.src == src_to_check and data_set_check(data_set) for data_set in event.payload.datasets
        )

    return filter_event


POLL_TIMEOUT_MS = 500


@pytest.mark.parametrize(
    "src,data_set_check",
    [(EXISTING_DATASET_WITH_DELAY, successful_dataset), (FAILING_DATASET_WITH_DELAY, failed_dataset)],
    ids=["successful", "failing"],
)
def test_fetcher(
    benchmark_event_dummy_payload: BenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    src: str,
    data_set_check: Callable[[DataSet], bool],
):
    benchmark_event = get_fetcher_benchmark_event(benchmark_event_dummy_payload, src)

    print(f"Sending event {benchmark_event}")

    kafka_producer_to_consume.send(
        kafka_service_config.consumer_topic, value=benchmark_event, key=benchmark_event.client_id
    )

    filter_event = get_message_is_the_response(benchmark_event, data_set_check)

    while True:
        records = kafka_consumer_of_produced.poll(POLL_TIMEOUT_MS)
        print("Got this:")
        print(records)
        kafka_consumer_of_produced.commit()
        for topic, recs in records.items():
            for msg in recs:
                if filter_event(msg.value):
                    return
