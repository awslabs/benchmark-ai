from subprocess import CalledProcessError

import pytest
from bai_kafka_utils.events import FetcherBenchmarkEvent, BenchmarkDoc, FetcherPayload, create_from_object, BenchmarkJob
from bai_kafka_utils.executors.descriptor import DescriptorError
from bai_kafka_utils.executors.execution_callback import ExecutionEngineException, NoResourcesFoundException
from bai_kafka_utils.utils import DEFAULT_ENCODING
from mock import call
from pytest import fixture

import executor
from executor.config import ExecutorConfig
from executor.k8s_execution_engine import K8SExecutionEngine, NoK8sResourcesFoundError

ACTION_ID = "ACTION_ID"

CLIENT_ID = "CLIENT_ID"

SOME_YAML = "yaml"
SOME_YAML_ENCODED = SOME_YAML.encode(DEFAULT_ENCODING)

KUBECTL = "/usr/local/bin/kubectl"


@fixture
def benchmark_doc() -> BenchmarkDoc:
    return BenchmarkDoc({"var": "val"}, "var = val", sha1="123")


@fixture
def valid_fetcher_event(benchmark_event, benchmark_doc: BenchmarkDoc) -> FetcherBenchmarkEvent:
    payload = FetcherPayload(
        toml=benchmark_doc,
        # We don't care about datasets here
        datasets=[],
    )
    return create_from_object(FetcherBenchmarkEvent, benchmark_event, payload=payload)


@fixture
def mock_engine_config() -> ExecutorConfig:
    # The Config is invalid in general, but enough for our tests
    return ExecutorConfig(kubectl=KUBECTL, descriptor_config=None, bai_config=None, environment_info=None)


@fixture
def k8s_execution_engine(mock_engine_config: ExecutorConfig) -> K8SExecutionEngine:
    return K8SExecutionEngine(mock_engine_config)


@fixture
def mock_subprocess_check_output(mocker):
    return mocker.patch.object(executor.k8s_execution_engine, "check_output", autospec=True)


@fixture
def mock_failing_subprocess_check_output(mock_subprocess_check_output):
    mock_subprocess_check_output.side_effect = CalledProcessError(returncode=1, cmd=KUBECTL)
    return mock_subprocess_check_output


@fixture
def mock_create_job_yaml_spec(mocker):
    return mocker.patch.object(
        executor.k8s_execution_engine, "create_job_yaml_spec", autospec=True, return_value=SOME_YAML
    )


@fixture
def mock_fail_create_job_yaml_spec(mock_create_job_yaml_spec):
    mock_create_job_yaml_spec.side_effect = DescriptorError()
    return mock_create_job_yaml_spec


def test_k8s_engine_happy_path(
    k8s_execution_engine: K8SExecutionEngine,
    valid_fetcher_event: FetcherBenchmarkEvent,
    mock_subprocess_check_output,
    mock_create_job_yaml_spec,
):
    job = k8s_execution_engine.run(valid_fetcher_event)
    mock_subprocess_check_output.assert_called_once_with([KUBECTL, "apply", "-f", "-"], input=SOME_YAML_ENCODED)

    assert job == BenchmarkJob(
        id=K8SExecutionEngine.JOB_ID_PREFIX + valid_fetcher_event.action_id,
        extras={K8SExecutionEngine.EXTRA_K8S_YAML: SOME_YAML},
    )


def test_raise_process_exception(
    k8s_execution_engine: K8SExecutionEngine,
    valid_fetcher_event: FetcherBenchmarkEvent,
    mock_failing_subprocess_check_output,
    mock_create_job_yaml_spec,
):
    with pytest.raises(ExecutionEngineException):
        k8s_execution_engine.run(valid_fetcher_event)


def test_raise_yaml_exception(
    k8s_execution_engine: K8SExecutionEngine,
    valid_fetcher_event: FetcherBenchmarkEvent,
    mock_subprocess_check_output,
    mock_fail_create_job_yaml_spec,
):
    with pytest.raises(ExecutionEngineException):
        k8s_execution_engine.run(valid_fetcher_event)


@fixture
def mock_check_output(mocker):
    return mocker.patch.object(executor.k8s_execution_engine, "check_output", return_value=b"something")


@fixture
def mock_check_output_with_parent_not_found(mocker):
    return mocker.patch.object(
        executor.k8s_execution_engine,
        "check_output",
        side_effect=[
            # Resource deletion fails
            NoK8sResourcesFoundError("Not found"),
            # Resources spawned by the scheduled job are found
            b"resources deleted successfully",
        ],
    )


@fixture
def mock_check_output_no_resource_found(mocker):
    return mocker.patch.object(
        executor.k8s_execution_engine,
        "check_output",
        side_effect=[
            # Resource deletion fails
            NoK8sResourcesFoundError("Not found"),
            # Resources spawned by the scheduled job are not found
            NoK8sResourcesFoundError("No spawned jobs found"),
        ],
    )


JOINED_RESOURCE_TYPES = ",".join(K8SExecutionEngine.ALL_K8S_RESOURCE_TYPES)


def test_cancel_benchmark_without_cascade(k8s_execution_engine: K8SExecutionEngine, mock_check_output):
    k8s_execution_engine.cancel(CLIENT_ID, ACTION_ID, cascade=False)

    expected_call = [
        KUBECTL,
        "delete",
        JOINED_RESOURCE_TYPES,
        "--selector",
        K8SExecutionEngine._create_label_selector(CLIENT_ID, ACTION_ID, as_parent=False),
    ]
    mock_check_output.assert_called_with(expected_call)


def test_cancel_benchmark_with_cascade(k8s_execution_engine: K8SExecutionEngine, mock_check_output):
    k8s_execution_engine.cancel(CLIENT_ID, ACTION_ID, cascade=True)

    expected_calls = [
        # Deletes resources with label action-id=<action_id>
        call(
            [
                KUBECTL,
                "delete",
                JOINED_RESOURCE_TYPES,
                "--selector",
                K8SExecutionEngine._create_label_selector(CLIENT_ID, ACTION_ID, as_parent=False),
            ]
        ),
        # Also deletes resources with label parent-action-id=<action_id>
        call(
            [
                KUBECTL,
                "delete",
                JOINED_RESOURCE_TYPES,
                "--selector",
                K8SExecutionEngine._create_label_selector(CLIENT_ID, ACTION_ID, as_parent=True),
            ]
        ),
    ]
    mock_check_output.assert_has_calls(expected_calls)


def test_cancel_without_cascade_fails(k8s_execution_engine: K8SExecutionEngine, mock_check_output_no_resource_found):
    with pytest.raises(NoResourcesFoundException):
        k8s_execution_engine.cancel(CLIENT_ID, ACTION_ID, cascade=False)


def test_cancel_with_cascade_fails(k8s_execution_engine: K8SExecutionEngine, mock_check_output_no_resource_found):
    with pytest.raises(NoResourcesFoundException):
        k8s_execution_engine.cancel(CLIENT_ID, ACTION_ID, cascade=False)


def test_cancel_benchmark_with_cascade_with_not_found_exception(
    k8s_execution_engine: K8SExecutionEngine, mock_check_output_with_parent_not_found
):
    """
    Tests that when deleting a benchmark with cascade, an attempt to cascade the deletion
    is still made even in the case that the scheduled benchmark is not found. E.g. if the user
    deletes a scheduled benchmark without cascading, they should still be able to delete the
    scheduled job's spawned jobs.
    """
    k8s_execution_engine.cancel(CLIENT_ID, ACTION_ID, cascade=True)

    expected_calls = [
        # Deletes resources with label action-id=<action_id>
        call(
            [
                KUBECTL,
                "delete",
                JOINED_RESOURCE_TYPES,
                "--selector",
                K8SExecutionEngine._create_label_selector(CLIENT_ID, ACTION_ID, as_parent=False),
            ]
        ),
        # Also deletes resources with label parent-action-id=<action_id>
        call(
            [
                KUBECTL,
                "delete",
                JOINED_RESOURCE_TYPES,
                "--selector",
                K8SExecutionEngine._create_label_selector(CLIENT_ID, ACTION_ID, as_parent=True),
            ]
        ),
    ]

    mock_check_output_with_parent_not_found.assert_has_calls(expected_calls)
