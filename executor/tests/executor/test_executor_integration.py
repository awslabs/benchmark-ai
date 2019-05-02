import uuid
from typing import Callable

import mock
import toml
import json

from pytest import fixture
from bai_kafka_utils.events import FetcherPayload, ExecutorPayload, BenchmarkDoc, BenchmarkEvent, DataSet, BenchmarkJob
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer


JOB_ID = "728ff542-b332-4520-bb2e-51d5e32cfc0a"
POLL_TIMEOUT_MS = 500

kafka_cfg = KafkaServiceConfig(
    consumer_group_id="CONSUMER_GROUP_ID",
    producer_topic="BAI_APP_FETCHER",
    consumer_topic="BAI_APP_EXECUTOR",
    bootstrap_servers=["localhost:9092"],
    logging_level="INFO"
)

consumer, producer = create_kafka_consumer_producer(kafka_cfg, ExecutorPayload)


@fixture
def benchmark_event(shared_datadir):
    descriptor_path = str(shared_datadir / "hello-world.toml")
    descriptor_as_dict = toml.load(descriptor_path)
    doc = BenchmarkDoc(
        contents=json.dumps(descriptor_as_dict),
        md5='MD5',
        doc='doc'
    )

    payload = FetcherPayload(toml=doc,
                             data_sets=[])

    return BenchmarkEvent(request_id=uuid.uuid4().hex,
                          message_id="MESSAGE_ID",
                          client_id="CLIENT_ID",
                          client_version="CLIENT_VERSION",
                          client_user="CLIENT_USER",
                          authenticated=False,
                          date=42,
                          visited=[],
                          payload=payload)


def get_message_is_the_response(src_event: BenchmarkEvent) -> Callable[[BenchmarkEvent], bool]:

    def filter_event(event: BenchmarkEvent) -> bool:
        return isinstance(event.payload, ExecutorPayload) and \
               event.request_id == src_event.request_id

    return filter_event


def get_event_equals(src_event: BenchmarkEvent) -> Callable[[BenchmarkEvent], bool]:
    # TODO: Improve this equals
    def same_event(event: BenchmarkEvent) -> bool:
        return src_event.request_id == event.request_id and \
               src_event.client_id == event.client_id and \
               src_event.payload.toml == event.payload.toml and \
               src_event.payload.data_sets == event.payload.data_sets

    return same_event


@mock.patch('transpiler.bai_knowledge.uuid.UUID', return_value=JOB_ID)
def test_producer(mock_uuid, benchmark_event):
    expected_job = BenchmarkJob(
        id=JOB_ID,
        status='SUBMITTED',
        k8s_yaml=''
    )
    expected_payload = ExecutorPayload.from_fetcher_payload(benchmark_event.payload, job=expected_job)
    expected_event = BenchmarkEvent.from_event_new_payload(benchmark_event, expected_payload)
    producer.send(kafka_cfg.producer_topic, benchmark_event)

    filter_event = get_message_is_the_response(benchmark_event)
    is_expected_event = get_event_equals(expected_event)

    # HACK to compare all fields of the events except the kubernetes yaml
    # expected_event.payload.job.k8s_yaml = received_event.payload.job.k8s_yaml

    while True:
        records = consumer.poll(POLL_TIMEOUT_MS)
        for topic, recs in records.items():
            for msg in recs:
                if filter_event(msg.value):
                    assert is_expected_event(msg.value)
                    return
