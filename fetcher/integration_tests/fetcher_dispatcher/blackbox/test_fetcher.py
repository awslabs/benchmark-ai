import pytest
from kafka import KafkaConsumer, KafkaProducer
from pytest import fixture
from time import time
from typing import Callable

from bai_kafka_utils.events import FetcherPayload, BenchmarkDoc, BenchmarkEvent, DataSet, FetcherBenchmarkEvent
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer
from bai_kafka_utils.kafka_service import KafkaServiceConfig

TIMEOUT_FOR_DOWNLOAD_SEC = 60


# Should be successful in any environment
EXISTING_DATASET = "http://files.grouplens.org/datasets/movielens/ml-1m.zip?delay"

# Should fail in any environment
FAILING_DATASET = "http://files.grouplens.org/datasets/movielens/fail.zip?delay"


def get_salted_src(src: str) -> str:
    cur_time = time()
    return f"{src}?time={cur_time}"


def get_benchmark_event(src: str):
    doc = BenchmarkDoc({"var": "val"}, "var = val", "")
    payload = FetcherPayload(toml=doc, datasets=[DataSet(src=get_salted_src(src))])
    return BenchmarkEvent(
        action_id="ACTION_ID",
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="CLIENT_VERSION",
        client_username="CLIENT_USER",
        authenticated=False,
        tstamp=42,
        visited=[],
        payload=payload,
    )


def successful_dataset(data_set: DataSet) -> bool:
    return data_set.dst is not None


def failed_dataset(data_set: DataSet) -> bool:
    return data_set.dst is None and data_set.message is not None


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


@fixture
def kafka_consumer_of_produced(kafka_service_config: KafkaServiceConfig):
    print(f"Creating a consumer with {kafka_service_config}...\n")
    return create_kafka_consumer(
        kafka_service_config.bootstrap_servers,
        kafka_service_config.consumer_group_id,
        # Yes. We consume, what the service has produced
        kafka_service_config.producer_topic,
        FetcherBenchmarkEvent,
    )


@fixture
def kafka_producer_to_consume(kafka_service_config: KafkaServiceConfig):
    print("Creating a producer...\n")
    return create_kafka_producer(kafka_service_config.bootstrap_servers)


TIME_TO_REBALANCE = 10


@pytest.mark.timeout(TIMEOUT_FOR_DOWNLOAD_SEC)
@pytest.mark.parametrize(
    "src,data_set_check", [(EXISTING_DATASET, successful_dataset), (FAILING_DATASET, failed_dataset)]
)
def test_fetcher(
    kafka_producer_to_consume: KafkaProducer,
    kafka_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    src: str,
    data_set_check: Callable[[DataSet], bool],
):
    benchmark_event = get_benchmark_event(src)

    print(f"Sending event {benchmark_event}")

    kafka_producer_to_consume.send(
        kafka_service_config.consumer_topic, value=benchmark_event, key=benchmark_event.client_id
    )

    filter_event = get_message_is_the_response(benchmark_event, data_set_check)

    try:
        while True:
            records = kafka_consumer_of_produced.poll(POLL_TIMEOUT_MS)
            print("Got this:")
            print(records)
            kafka_consumer_of_produced.commit()
            for topic, recs in records.items():
                for msg in recs:
                    if filter_event(msg.value):
                        return
    finally:
        kafka_consumer_of_produced.close()
        kafka_producer_to_consume.close()
