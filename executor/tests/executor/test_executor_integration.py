import pytest

from typing import Callable
from bai_kafka_utils.events import ExecutorBenchmarkEvent, BenchmarkEvent, BenchmarkJob, ExecutorPayload
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer


JOB_ID = "728ff542-b332-4520-bb2e-51d5e32cfc0a"
POLL_TIMEOUT_MS = 500

kafka_cfg = KafkaServiceConfig(
    consumer_group_id="CONSUMER_GROUP_ID",
    producer_topic="BAI_APP_FETCHER",
    consumer_topic="BAI_APP_EXECUTOR",
    bootstrap_servers=["localhost:9092"],
    logging_level="INFO",
)


def get_message_is_the_response(src_event: BenchmarkEvent) -> Callable[[BenchmarkEvent], bool]:
    def filter_event(event: BenchmarkEvent) -> bool:
        return isinstance(event.payload, ExecutorPayload) and event.action_id == src_event.action_id

    return filter_event


def get_event_equals(src_event: BenchmarkEvent) -> Callable[[BenchmarkEvent], bool]:
    # TODO: Improve this equals
    def same_event(event: BenchmarkEvent) -> bool:
        return (
            src_event.action_id == event.action_id
            and src_event.client_id == event.client_id
            and src_event.payload.toml == event.payload.toml
            and src_event.payload.datasets == event.payload.datasets
        )

    return same_event


@pytest.mark.skip(
    reason="This test requires the executor service to be running on your machine, along with Kafka, ZK, etc"
)
def test_producer(benchmark_event):
    consumer, producer = create_kafka_consumer_producer(kafka_cfg, ExecutorBenchmarkEvent)

    expected_job = BenchmarkJob(id=JOB_ID, status="SUBMITTED", k8s_yaml="")
    expected_payload = ExecutorPayload.from_fetcher_payload(benchmark_event.payload, job=expected_job)
    expected_event = BenchmarkEvent.from_event_new_payload(benchmark_event, expected_payload)
    producer.send(kafka_cfg.producer_topic, benchmark_event)

    filter_event = get_message_is_the_response(benchmark_event)
    is_expected_event = get_event_equals(expected_event)

    while True:
        records = consumer.poll(POLL_TIMEOUT_MS)
        for topic, recs in records.items():
            for msg in recs:
                if filter_event(msg.value):
                    assert is_expected_event(msg.value)
                    consumer.close()
                    return
