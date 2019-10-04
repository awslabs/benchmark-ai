import dataclasses

import pytest
from kafka import KafkaProducer, KafkaConsumer
from time import time
from typing import Callable

from bai_kafka_utils.cmd_callback import KafkaCommandCallback
from bai_kafka_utils.events import (
    BenchmarkEvent,
    DownloadableContent,
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
    get_cancel_event,
)
from bai_kafka_utils.kafka_service import KafkaServiceConfig

DataSetFilter = Callable[[DownloadableContent], bool]


# Should be successful in any environment - has delay of 10s for consumer group to setup
EXISTING_CONTENT_WITH_DELAY = "http://files.grouplens.org/datasets/movielens/ml-1m.zip?delay"

# Should fail in any environment - has delay of 10s for consumer group to setup
FAILING_CONTENT_WITH_DELAY = "http://files.grouplens.org/datasets/movielens/fail.zip?delay"


def get_salted_src(src: str) -> str:
    cur_time = time()
    return f"{src}?time={cur_time}"


def get_fetcher_benchmark_event(template_event: BenchmarkEvent, dataset_src: str, model_src: str):
    doc = BenchmarkDoc({"var": "val"}, "var = val", "")
    datasets = [] if not dataset_src else [DownloadableContent(src=get_salted_src(dataset_src), path="/mount/path")]
    models = [] if not model_src else [DownloadableContent(src=get_salted_src(model_src), path="/mount/path")]
    fetch_payload = FetcherPayload(toml=doc, datasets=datasets, models=models)
    return dataclasses.replace(template_event, payload=fetch_payload)


def is_dataset_successful(content: DownloadableContent) -> bool:
    return content.dst is not None and content.type == FetchedType.FILE and content.status == FetcherStatus.DONE


def get_is_fetch_response_filter(src_event: BenchmarkEvent, kafka_service_config: KafkaServiceConfig) -> EventFilter:
    src_to_check = (src_event.payload.datasets or src_event.payload.models)[0].src

    def filter_fetcher_event(event: BenchmarkEvent) -> bool:

        return (
            event.type == kafka_service_config.producer_topic
            and isinstance(event.payload, FetcherPayload)
            and any(
                data_set.src == src_to_check and is_dataset_successful(data_set)
                for data_set in event.payload.datasets + event.payload.models
            )
        )

    return filter_fetcher_event


@pytest.mark.parametrize(
    "dataset_src,model_src,expected_status",
    [
        # data set download only
        (EXISTING_CONTENT_WITH_DELAY, None, Status.SUCCEEDED),
        (FAILING_CONTENT_WITH_DELAY, None, Status.FAILED),
        # model download only
        (None, EXISTING_CONTENT_WITH_DELAY, Status.SUCCEEDED),
        (None, FAILING_CONTENT_WITH_DELAY, Status.FAILED),
        # both data set and model downloads
        (EXISTING_CONTENT_WITH_DELAY, EXISTING_CONTENT_WITH_DELAY, Status.SUCCEEDED),
        (FAILING_CONTENT_WITH_DELAY, EXISTING_CONTENT_WITH_DELAY, Status.FAILED),
        (EXISTING_CONTENT_WITH_DELAY, FAILING_CONTENT_WITH_DELAY, Status.FAILED),
    ],
    ids=[
        "dataset_only_successful",
        "dataset_only_failing",
        "model_only_successful",
        "model_only_failing",
        "dataset_and_model_successful",
        "dataset_failing_model_successful",
        "dataset_successful_model_failing",
    ],
)
def test_fetcher(
    benchmark_event_dummy_payload: BenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    dataset_src: str,
    model_src: str,
    expected_status: Status,
):
    benchmark_event = send_salted_fetch_request(
        benchmark_event_dummy_payload,
        kafka_producer_to_consume,
        kafka_service_config.consumer_topic,
        dataset_src,
        model_src,
    )

    status_event_filter = get_is_status_filter(benchmark_event, expected_status, kafka_service_config)
    filters = [status_event_filter]

    if expected_status == Status.SUCCEEDED:
        fetcher_event_filter = get_is_fetch_response_filter(benchmark_event, kafka_service_config)
        filters.append(fetcher_event_filter)

    combined_filter = CombinedFilter(filters)

    return wait_for_response(combined_filter, kafka_consumer_of_produced)


@pytest.mark.parametrize(
    "dataset_src,model_src",
    [
        # data set download only
        (EXISTING_CONTENT_WITH_DELAY, None),
        # models only
        (None, EXISTING_CONTENT_WITH_DELAY),
        # both data set and model downloads
        (EXISTING_CONTENT_WITH_DELAY, EXISTING_CONTENT_WITH_DELAY),
    ],
    ids=["dataset_only", "model_only", "dataset_and_model"],
)
def test_cancel(
    benchmark_event_dummy_payload: BenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    dataset_src,
    model_src,
):
    benchmark_event = send_salted_fetch_request(
        benchmark_event_dummy_payload,
        kafka_producer_to_consume,
        kafka_service_config.consumer_topic,
        dataset_src=dataset_src,
        model_src=model_src,
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


def send_salted_fetch_request(benchmark_event_dummy_payload, kafka_producer_to_consume, topic, dataset_src, model_src):
    benchmark_event = get_fetcher_benchmark_event(benchmark_event_dummy_payload, dataset_src, model_src)
    print(f"Sending event {benchmark_event}")
    kafka_producer_to_consume.send(topic, value=benchmark_event, key=benchmark_event.client_id)
    return benchmark_event
