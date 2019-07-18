from bai_kafka_utils.events import BenchmarkDoc, FetcherPayload, create_from_object, FetcherBenchmarkEvent
from bai_kafka_utils.kafka_service import KafkaService
from kafka import KafkaConsumer, KafkaProducer
from pytest import fixture
from unittest.mock import MagicMock

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
def benchmark_doc() -> BenchmarkDoc:
    return BenchmarkDoc({"var": "val"}, "var = val", sha1="123")


@fixture
def benchmark_event_with_data_sets(benchmark_event, benchmark_doc: BenchmarkDoc) -> FetcherBenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, datasets=[])
    return create_from_object(FetcherBenchmarkEvent, benchmark_event, payload=payload)


@fixture
def executor_callback(config_args, config_env, kafka_service_config) -> ExecutorEventHandler:
    config = create_executor_config(config_args, config_env)
    return ExecutorEventHandler(config, kafka_service_config.producer_topic)


def test_create_executor(mocker, config_args, config_env, kafka_service_config):
    mock_consumer = MagicMock(spec=KafkaConsumer)
    mock_producer = MagicMock(spec=KafkaProducer)
    mock_create_consumer_producer = mocker.patch(
        "executor.executor.create_kafka_consumer_producer", return_value=(mock_consumer, mock_producer), autospec=True
    )

    executor_config = create_executor_config(config_args, config_env)
    executor = create_executor(kafka_service_config, executor_config)

    mock_create_consumer_producer.assert_called_once()
    assert isinstance(executor, KafkaService)
    assert kafka_service_config.consumer_topic in executor._callbacks
    assert kafka_service_config.cmd_submit_topic in executor._callbacks
