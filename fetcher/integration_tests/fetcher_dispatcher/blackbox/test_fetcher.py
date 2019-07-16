import dataclasses

import pytest
from kafka import KafkaProducer, KafkaConsumer
from time import time
from typing import Callable

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
)
from bai_kafka_utils.integration_tests.test_loop import (
    CombinedFilter,
    wait_for_response,
    EventFilter,
    get_is_status_filter,
    get_is_command_return_filter,
)
from bai_kafka_utils.kafka_service import KafkaServiceConfig

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
    cancel_payload = CommandRequestPayload(command="cancel", args={"target_action_id": template_event.action_id})
    return dataclasses.replace(
        template_event, payload=cancel_payload, action_id=template_event.action_id + "_cancel", type=cmd_submit_topic
    )


def is_dataset_successful(data_set: DataSet) -> bool:
    return data_set.dst is not None and data_set.type == FetchedType.FILE and data_set.status == FetcherStatus.DONE


def get_is_fetch_response_filter(src_event: BenchmarkEvent, kafka_service_config: KafkaServiceConfig) -> EventFilter:
    src_to_check = src_event.payload.datasets[0].src

    def filter_fetcher_event(event: BenchmarkEvent) -> bool:

        return (
            event.type == kafka_service_config.producer_topic
            and isinstance(event.payload, FetcherPayload)
            and any(
                data_set.src == src_to_check and is_dataset_successful(data_set) for data_set in event.payload.datasets
            )
        )

    return filter_fetcher_event


@pytest.mark.parametrize(
    "src,expected_status",
    [(EXISTING_DATASET_WITH_DELAY, Status.SUCCEEDED), (FAILING_DATASET_WITH_DELAY, Status.FAILED)],
    ids=["successful", "failing"],
)
def test_fetcher(
    benchmark_event_dummy_payload: BenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    src: str,
    expected_status: Status,
):
    benchmark_event = send_salted_fetch_request(
        benchmark_event_dummy_payload, kafka_producer_to_consume, kafka_service_config.consumer_topic, src
    )

    status_event_filter = get_is_status_filter(benchmark_event, expected_status, kafka_service_config)
    filters = [status_event_filter]

    if expected_status == Status.SUCCEEDED:
        fetcher_event_filter = get_is_fetch_response_filter(benchmark_event, kafka_service_config)
        filters.append(fetcher_event_filter)

    combined_filter = CombinedFilter(filters)

    return wait_for_response(combined_filter, kafka_consumer_of_produced)


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

    status_event_filter = get_is_status_filter(benchmark_event, Status.CANCELED, kafka_service_config)
    command_return_filter = get_is_command_return_filter(
        cancel_event, KafkaCommandCallback.CODE_SUCCESS, kafka_service_config
    )
    combined_filter = CombinedFilter([status_event_filter, command_return_filter])

    return wait_for_response(combined_filter, kafka_consumer_of_produced)


def send_salted_fetch_request(benchmark_event_dummy_payload, kafka_producer_to_consume, topic, dataset_src):
    benchmark_event = get_fetcher_benchmark_event(benchmark_event_dummy_payload, dataset_src)
    print(f"Sending event {benchmark_event}")
    kafka_producer_to_consume.send(topic, value=benchmark_event, key=benchmark_event.client_id)
    return benchmark_event
