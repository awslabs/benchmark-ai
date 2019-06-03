from _pytest.fixtures import fixture

from bai_kafka_utils.events import FetcherBenchmarkEvent, BenchmarkJob, ExecutorPayload
from bai_kafka_utils.kafka_service import KafkaService

from bai_kafka_utils.utils import DEFAULT_ENCODING
from executor.args import create_executor_config
from executor.executor import ExecutorEventHandler, KubernetesExecutionEngine

JOB_YAML = "test yaml"


@fixture
def kubernetes_exec_engine(config_args):
    config = create_executor_config(config_args)
    return KubernetesExecutionEngine(config)


def test_kubernetes_exec_engine_apply(mocker, kubernetes_exec_engine: KubernetesExecutionEngine, config_args):
    mock_check_output = mocker.patch("executor.executor.subprocess.check_output")

    config = create_executor_config(config_args)
    kubernetes_exec_engine._kubernetes_apply(JOB_YAML)
    expected_args = [config.kubectl, "apply", "-f", "-"]

    mock_check_output.assert_called_once()
    # https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock.call_args
    args, kwargs = mock_check_output.call_args
    assert args[0] == expected_args
    assert kwargs == {"input": JOB_YAML.encode(DEFAULT_ENCODING)}


def test_kubernetes_engine_run_benchmark(
    mocker,
    benchmark_event_with_data_sets: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    kubernetes_exec_engine: KubernetesExecutionEngine,
    executor_callback: ExecutorEventHandler,
):
    mock_check_output = mocker.patch("executor.executor.subprocess.check_output")
    mock_create_yaml = mocker.patch("executor.executor.create_job_yaml_spec", return_value=JOB_YAML)

    expected_job = BenchmarkJob(id=benchmark_event_with_data_sets.action_id, k8s_yaml=JOB_YAML)
    expected_payload = ExecutorPayload.create_from_fetcher_payload(benchmark_event_with_data_sets.payload, expected_job)

    kubernetes_exec_engine.run_benchmark(benchmark_event_with_data_sets, kafka_service, executor_callback)
    event_to_send = kafka_service.send_event.call_args_list[0][0][0]

    mock_create_yaml.assert_called_once()
    mock_check_output.assert_called_once()
    assert event_to_send.action_id == benchmark_event_with_data_sets.action_id
    assert event_to_send.payload == expected_payload
