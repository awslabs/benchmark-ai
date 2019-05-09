import kafka
from unittest import mock

from pytest import fixture
from unittest.mock import MagicMock, patch
from bai_kafka_utils.events import BenchmarkDoc, BenchmarkEvent, FetcherPayload, DataSet
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import DEFAULT_ENCODING
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


@fixture
def kafka_service() -> KafkaService:
    return MagicMock(spec=KafkaService)


@fixture
def benchmark_doc() -> BenchmarkDoc:
    return BenchmarkDoc({"var": "val"}, "var = val", sha1="123")


def get_benchmark_event(payload):
    return BenchmarkEvent(
        action_id="action_id",
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="CLIENT_VERSION",
        client_username="client_username",
        authenticated=False,
        tstamp=42,
        visited=[],
        payload=payload,
    )


@fixture
def benchmark_event_with_data_sets(benchmark_doc: BenchmarkDoc) -> BenchmarkEvent:
    payload = FetcherPayload(
        toml=benchmark_doc,
        datasets=[DataSet(src="src1", dst="s3://bucket/object"), DataSet(src="src2", dst="s3://bucket/object2")],
    )
    return get_benchmark_event(payload)


@fixture
def benchmark_event_without_data_sets(benchmark_doc: BenchmarkDoc) -> BenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, datasets=[])
    return get_benchmark_event(payload)


@mock.patch("executor.executor.subprocess.check_output")
@mock.patch("executor.executor.create_job_yaml_spec", return_value=(JOB_ID, "yaml_spec"))
def test_executor_event_handler_handle_event(
    mock_create_yaml,
    mock_check_output,
    benchmark_event_with_data_sets: BenchmarkEvent,
    kafka_service: KafkaService,
    config_args,
):
    config = create_executor_config(config_args)
    executor_callback = ExecutorEventHandler(config)

    event_to_send = executor_callback.handle_event(benchmark_event_with_data_sets, kafka_service)

    mock_create_yaml.assert_called_once()
    mock_check_output.assert_called_once()
    assert event_to_send.action_id == benchmark_event_with_data_sets.action_id


@mock.patch("executor.executor.subprocess.check_output")
def test_executor_event_handler_k8s_apply(mock_check_output, config_args):
    config = create_executor_config(config_args)
    executor_callback = ExecutorEventHandler(config)

    yaml = "test yaml"
    executor_callback._kubernetes_apply(yaml)

    expected_args = [config.kubectl, "apply", "-f", "-"]

    mock_check_output.assert_called_once()
    # https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock.call_args
    args, kwargs = mock_check_output.call_args
    assert args[0] == expected_args
    assert kwargs == {"input": yaml.encode(DEFAULT_ENCODING)}


@patch.object(kafka, "KafkaProducer")
@patch.object(kafka, "KafkaConsumer")
def test_create_executor(mockKafkaConsumer, mockKafkaProducer, config_args):
    kafka_service_config = KafkaServiceConfig(
        bootstrap_servers=MOCK_KAFKA_BOOTSTRAP_SERVERS,
        consumer_group_id=MOCK_CONSUMER_GROUP_ID,
        consumer_topic=MOCK_CONSUMER_TOPIC,
        logging_level=LOGGING_LEVEL,
        producer_topic=MOCK_PRODUCER_TOPIC,
    )
    executor_config = create_executor_config(config_args)
    executor = create_executor(kafka_service_config, executor_config)

    mockKafkaConsumer.assert_called_once()
    mockKafkaProducer.assert_called_once()

    assert executor
