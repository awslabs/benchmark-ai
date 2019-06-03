from bai_kafka_utils.kafka_service import KafkaService
from kafka import KafkaConsumer, KafkaProducer
from pytest import fixture
from unittest.mock import MagicMock
from bai_kafka_utils.events import (
    BenchmarkDoc,
    BenchmarkJob,
    FetcherPayload,
    ExecutorPayload,
    create_from_object,
    FetcherBenchmarkEvent,
    ExecutorBenchmarkEvent,
)
from executor.args import create_executor_config
from executor.executor import ExecutorEventHandler, create_executor

LOGGING_LEVEL = "DEBUG"

MOCK_SERVICE_NAME = "AMAZING_SOFT"
MOCK_CONSUMER_GROUP_ID = "GROUP_ID"
MOCK_KAFKA1 = "kafka1:9092"
MOCK_KAFKA2 = "kafka2:9092"
MOCK_PRODUCER_TOPIC = "OUT_TOPIC"
MOCK_CONSUMER_TOPIC = "IN_TOPIC"

MOCK_KAFKA_BOOTSTRAP_SERVERS = [MOCK_KAFKA1, MOCK_KAFKA2]

JOB_ID = "728ff542-b332-4520-bb2e-51d5e32cfc0a"
JOB_YAML = "test yaml"


@fixture
def benchmark_event_without_data_sets(benchmark_event, benchmark_doc: BenchmarkDoc) -> FetcherBenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, datasets=[])
    return create_from_object(FetcherBenchmarkEvent, benchmark_event, payload=payload)


def test_create_response_event(benchmark_event_with_data_sets, executor_callback: ExecutorEventHandler):
    expected_job = BenchmarkJob(id=JOB_ID, k8s_yaml=JOB_YAML)
    expected_payload = ExecutorPayload.create_from_fetcher_payload(benchmark_event_with_data_sets.payload, expected_job)
    expected_event = create_from_object(
        ExecutorBenchmarkEvent, benchmark_event_with_data_sets, payload=expected_payload
    )

    response_event = executor_callback._create_response_event(benchmark_event_with_data_sets, JOB_ID, JOB_YAML)

    assert expected_event == response_event


def test_create_executor(mocker, config_args, kafka_service_config):
    mock_consumer = MagicMock(spec=KafkaConsumer)
    mock_producer = MagicMock(spec=KafkaProducer)
    mock_create_consumer_producer = mocker.patch(
        "executor.executor.create_kafka_consumer_producer", return_value=(mock_consumer, mock_producer), autospec=True
    )

    executor_config = create_executor_config(config_args)
    executor = create_executor(kafka_service_config, executor_config)

    mock_create_consumer_producer.assert_called_once()
    assert executor


def test_executor_event_handler_handle_event(
    mocker,
    benchmark_event_with_data_sets: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    executor_callback: ExecutorEventHandler,
):
    mock_kubernetes_engine = mocker.patch("executor.executor.KubernetesExecutionEngine", create_autospec=True)

    executor_callback.execution_engines = {"kubernetes": mock_kubernetes_engine}
    executor_callback.handle_event(benchmark_event_with_data_sets, kafka_service)

    mock_kubernetes_engine.run_benchmark.assert_called_once()
    assert mock_kubernetes_engine.run_benchmark.call_args[0] == (
        benchmark_event_with_data_sets,
        kafka_service,
        executor_callback,
    )
