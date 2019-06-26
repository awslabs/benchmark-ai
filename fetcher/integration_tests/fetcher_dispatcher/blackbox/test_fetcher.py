import dataclasses

import pytest
from kafka import KafkaProducer, KafkaConsumer
from time import time
from typing import Callable, List

from bai_kafka_utils.cmd_callback import KafkaCommandCallback
from bai_kafka_utils.events import (
    BenchmarkEvent,
    CommandRequestPayload,
    DataSet,
    BenchmarkDoc,
    FetcherPayload,
    FetchedType,
    FetcherStatus,
    Status,
    CommandResponsePayload,
    CommandRequestEvent,
)
from bai_kafka_utils.kafka_service import KafkaServiceConfig

TIMEOUT_FOR_DOWNLOAD_SEC = 5 * 60

EventFilter = Callable[[BenchmarkEvent], bool]
DataSetFilter = Callable[[DataSet], bool]


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


def get_cancel_event(template_event: BenchmarkEvent, cmd_submit_topic: str):
    cancel_payload = CommandRequestPayload(command="delete", args={"target_action_id": template_event.action_id})
    return dataclasses.replace(
        template_event, payload=cancel_payload, action_id=template_event.action_id + "_cancel", type=cmd_submit_topic
    )


def successful_dataset(data_set: DataSet) -> bool:
    return data_set.dst is not None and data_set.type == FetchedType.FILE and data_set.status == FetcherStatus.DONE


def failed_dataset(data_set: DataSet) -> bool:
    return data_set.dst is None and data_set.message is not None and data_set.status == FetcherStatus.FAILED


def canceled_dataset(data_set: DataSet) -> bool:
    return data_set.dst is None and data_set.status == FetcherStatus.CANCELED


def get_is_fetch_response(
    src_event: BenchmarkEvent, data_set_check: DataSetFilter, kafka_service_config: KafkaServiceConfig
) -> EventFilter:
    src_to_check = src_event.payload.datasets[0].src

    def filter_fetcher_event(event: BenchmarkEvent) -> bool:

        return (
            event.type == kafka_service_config.producer_topic
            and isinstance(event.payload, FetcherPayload)
            and any(data_set.src == src_to_check and data_set_check(data_set) for data_set in event.payload.datasets)
        )

    return filter_fetcher_event


def get_is_status(src_event: BenchmarkEvent, status: Status, kafka_service_config: KafkaServiceConfig) -> EventFilter:
    def filter_status_event(event: BenchmarkEvent) -> bool:
        return (
            event.type == kafka_service_config.status_topic
            and event.action_id == src_event.action_id
            and event.status == status
        )

    return filter_status_event


def get_is_command_return(
    src_event: CommandRequestEvent, return_code: int, kafka_service_config: KafkaServiceConfig
) -> EventFilter:
    def filter_command_event(event: BenchmarkEvent) -> bool:
        if event.type != kafka_service_config.cmd_return_topic or not isinstance(event.payload, CommandResponsePayload):
            return False
        payload: CommandResponsePayload = event.payload
        return (
            payload.return_code == return_code
            and payload.cmd_submit.action_id == src_event.action_id
            and payload.cmd_submit.payload == src_event.payload
        )

    return filter_command_event


def get_all_complete(filters: List[EventFilter]) -> EventFilter:
    set_filters = set(filters)

    def filter_event(event: BenchmarkEvent) -> bool:
        for fltr in set_filters:
            if fltr(event):
                set_filters.remove(fltr)
                print(f"Hit condition {fltr.__name__}. {len(set_filters)} to hit.")
                break
        return not set_filters

    return filter_event


POLL_TIMEOUT_MS = 500


@pytest.mark.timeout(TIMEOUT_FOR_DOWNLOAD_SEC)
@pytest.mark.parametrize(
    "src,data_set_check,expected_status",
    [
        (EXISTING_DATASET_WITH_DELAY, successful_dataset, Status.SUCCEEDED),
        (FAILING_DATASET_WITH_DELAY, failed_dataset, Status.FAILED),
    ],
    ids=["successful", "failing"],
)
def test_fetcher(
    benchmark_event_dummy_payload: BenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    src: str,
    data_set_check: DataSetFilter,
    expected_status: Status,
):
    benchmark_event = send_salted_fetch_request(
        benchmark_event_dummy_payload, kafka_producer_to_consume, kafka_service_config.consumer_topic, src
    )

    fetcher_event_filter = get_is_fetch_response(benchmark_event, data_set_check, kafka_service_config)
    status_event_filter = get_is_status(benchmark_event, expected_status, kafka_service_config)
    combined_filter = get_all_complete([fetcher_event_filter, status_event_filter])

    return wait_for_response(combined_filter, kafka_consumer_of_produced)


@pytest.mark.timeout(TIMEOUT_FOR_DOWNLOAD_SEC)
def test_cancel(
    benchmark_event_dummy_payload: BenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
):
    benchmark_event = send_salted_fetch_request(
        benchmark_event_dummy_payload,
        kafka_producer_to_consume,
        kafka_service_config.consumer_topic,
        EXISTING_DATASET_WITH_DELAY,
    )
    cancel_event = get_cancel_event(benchmark_event, kafka_service_config.cmd_submit_topic)
    kafka_producer_to_consume.send(
        kafka_service_config.cmd_submit_topic, value=cancel_event, key=cancel_event.client_id
    )

    fetcher_event_filter = get_is_fetch_response(benchmark_event, canceled_dataset, kafka_service_config)
    status_event_filter = get_is_status(benchmark_event, Status.CANCELED, kafka_service_config)
    command_return_filter = get_is_command_return(cancel_event, KafkaCommandCallback.CODE_SUCCESS, kafka_service_config)
    combined_filter = get_all_complete([fetcher_event_filter, status_event_filter, command_return_filter])

    return wait_for_response(combined_filter, kafka_consumer_of_produced)


def send_salted_fetch_request(benchmark_event_dummy_payload, kafka_producer_to_consume, topic, dataset_src):
    benchmark_event = get_fetcher_benchmark_event(benchmark_event_dummy_payload, dataset_src)
    print(f"Sending event {benchmark_event}")
    kafka_producer_to_consume.send(topic, value=benchmark_event, key=benchmark_event.client_id)
    return benchmark_event


def wait_for_response(filter_event, kafka_consumer_of_produced):
    while True:
        records = kafka_consumer_of_produced.poll(POLL_TIMEOUT_MS)
        print("Got this:")
        print(records)
        kafka_consumer_of_produced.commit()
        for topic, recs in records.items():
            for msg in recs:
                print(f"Got evt {msg.value}")
                if filter_event(msg.value):
                    return
