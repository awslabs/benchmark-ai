from kafka import KafkaConsumer, KafkaProducer
from pytest import fixture
from unittest.mock import MagicMock
from bai_kafka_utils.events import (
    BenchmarkDoc,
    BenchmarkJob,
    FetcherPayload,
    ExecutorPayload,
    DataSet,
    create_from_object,
    FetcherBenchmarkEvent,
    ExecutorBenchmarkEvent,
)
from bai_kafka_utils.kafka_service import KafkaService
from bai_kafka_utils.utils import DEFAULT_ENCODING
from executor.args import create_executor_config
from executor.executor import ExecutorEventHandler, create_executor, JOB_ID_PREFIX

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
    payload = FetcherPayload(
        toml=benchmark_doc,
        datasets=[DataSet(src="src1", dst="s3://bucket/object"), DataSet(src="src2", dst="s3://bucket/object2")],
    )
    return create_from_object(FetcherBenchmarkEvent, benchmark_event, payload=payload)


@fixture
def benchmark_event_without_data_sets(benchmark_event, benchmark_doc: BenchmarkDoc) -> FetcherBenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, datasets=[])
    return create_from_object(FetcherBenchmarkEvent, benchmark_event, payload=payload)


@fixture
def executor_callback(config_args, config_env, kafka_service_config) -> ExecutorEventHandler:
    config = create_executor_config(config_args, config_env)
    return ExecutorEventHandler(config, kafka_service_config.producer_topic)


def test_executor_event_handler_handle_event(
    mocker,
    benchmark_event_with_data_sets: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    executor_callback: ExecutorEventHandler,
):
    mock_check_output = mocker.patch("executor.executor.subprocess.check_output")
    mock_create_yaml = mocker.patch("executor.executor.create_job_yaml_spec", return_value=JOB_YAML)

    expected_job = BenchmarkJob(id=JOB_ID_PREFIX + benchmark_event_with_data_sets.action_id, k8s_yaml=JOB_YAML)
    expected_payload = ExecutorPayload.create_from_fetcher_payload(benchmark_event_with_data_sets.payload, expected_job)

    executor_callback.handle_event(benchmark_event_with_data_sets, kafka_service)
    event_to_send = kafka_service.send_event.call_args_list[0][0][0]

    mock_create_yaml.assert_called_once()
    mock_check_output.assert_called_once()
    assert event_to_send.action_id == benchmark_event_with_data_sets.action_id
    assert event_to_send.payload.job == expected_payload.job
    assert event_to_send.payload == expected_payload


def test_executor_event_handler_k8s_apply(mocker, executor_callback: ExecutorEventHandler, config_args, config_env):
    mock_check_output = mocker.patch("executor.executor.subprocess.check_output")

    config = create_executor_config(config_args, config_env)
    executor_callback._kubernetes_apply(JOB_YAML)
    expected_args = [config.kubectl, "apply", "-f", "-"]

    mock_check_output.assert_called_once()
    # https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock.call_args
    args, kwargs = mock_check_output.call_args
    assert args[0] == expected_args
    assert kwargs == {"input": JOB_YAML.encode(DEFAULT_ENCODING)}


def test_create_response_event(benchmark_event_with_data_sets, executor_callback: ExecutorEventHandler):
    expected_job = BenchmarkJob(id=JOB_ID, k8s_yaml=JOB_YAML)
    expected_payload = ExecutorPayload.create_from_fetcher_payload(benchmark_event_with_data_sets.payload, expected_job)
    expected_event = create_from_object(
        ExecutorBenchmarkEvent, benchmark_event_with_data_sets, payload=expected_payload
    )

    response_event = executor_callback._create_response_event(benchmark_event_with_data_sets, JOB_ID, JOB_YAML)

    assert expected_event == response_event


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
