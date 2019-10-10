from unittest.mock import Mock, create_autospec, call, MagicMock

import kubernetes
import pytest
from kubernetes.client import V1Job, V1JobSpec, V1Pod, V1ObjectMeta, V1PodList, V1JobStatus, V1PodTemplate

from bai_watcher.kubernetes_job_watcher import KubernetesJobWatcher, SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS
from bai_watcher.status_inferrers.single_node import SingleNodeStrategyKubernetesStatusInferrer
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

JOB_START_TIME = 1000


@pytest.fixture
def mock_job() -> V1Job:
    meta = V1ObjectMeta(namespace="default", name="some-job")
    spec = V1JobSpec(template=V1PodTemplate())
    status = V1JobStatus(conditions=[])
    return V1Job(metadata=meta, spec=spec, status=status)


@pytest.fixture()
def mock_pod_list() -> V1PodList:
    meta = V1ObjectMeta(namespace="default", name="some-pod")
    pod = V1Pod(metadata=meta)
    return V1PodList(items=[pod])


@pytest.fixture
def mock_single_node_strategy_kubernetes_status_inferrer(mocker):
    return mocker.patch("bai_watcher.kubernetes_job_watcher.SingleNodeStrategyKubernetesStatusInferrer", auto_spec=True)


def mock_loop_dependencies(mocker, *, iterations, kubernetes_job_status):
    mocker.patch("itertools.count", return_value=[0] * iterations)
    mock_time_sleep = mocker.patch("time.sleep")
    mock_inferrer = create_autospec(SingleNodeStrategyKubernetesStatusInferrer)
    mock_inferrer.status = MagicMock(return_value=kubernetes_job_status)
    mocker.patch(
        "bai_watcher.kubernetes_job_watcher.SingleNodeStrategyKubernetesStatusInferrer", return_value=mock_inferrer
    )
    return mock_time_sleep


def create_fake_kubernetes_jobs_client(mocker) -> kubernetes.client.BatchV1Api:
    mocker.patch("bai_watcher.kubernetes_job_watcher.load_kubernetes_config", autospec=True)
    fake_kubernetes_client = create_autospec(kubernetes.client.BatchV1Api)
    return fake_kubernetes_client


@pytest.fixture
def k8s_job_watcher(mocker):
    mocker.patch("bai_watcher.kubernetes_job_watcher.load_kubernetes_config", autospec=True)
    watcher = KubernetesJobWatcher(
        "job-id-1234",
        callback=Mock(),
        kubernetes_namespace="default",
        kubernetes_client_jobs=create_autospec(kubernetes.client.BatchV1Api),
        kubernetes_client_pods=create_autospec(kubernetes.client.CoreV1Api),
    )
    watcher.job_start_time = JOB_START_TIME
    return watcher


def test_get_status_when_job_does_not_exist(k8s_job_watcher):
    k8s_job_watcher.jobs_client.read_namespaced_job_status.side_effect = kubernetes.client.rest.ApiException(status=404)
    assert k8s_job_watcher._get_status() == BenchmarkJobStatus.JOB_NOT_FOUND


@pytest.mark.parametrize("error_code", [500, 503])
def test_get_status_when_kubernetes_raises_a_server_error(k8s_job_watcher, error_code):
    k8s_job_watcher.jobs_client.read_namespaced_job_status.side_effect = kubernetes.client.rest.ApiException(
        status=error_code
    )
    with pytest.raises(kubernetes.client.rest.ApiException) as e:
        k8s_job_watcher._get_status()
    assert e.value.status == error_code


def test_thread_run_loop_when_callback_returns_true_will_end_loop(k8s_job_watcher, mocker):
    # HACK: Testing an internal API, but that's fine :)

    # setup mocks
    mock_time_sleep = mock_loop_dependencies(
        mocker, iterations=2, kubernetes_job_status=BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS
    )
    k8s_job_watcher._callback.return_value = True

    # evaluate
    k8s_job_watcher._thread_run_loop()

    # assertions
    assert k8s_job_watcher._callback.call_args_list == [
        call("job-id-1234", BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS)
    ]
    assert mock_time_sleep.call_args_list == []
    assert k8s_job_watcher.get_result() == (True, None)


def test_thread_run_loop_when_callback_returns_raises_will_end_loop(k8s_job_watcher, mocker):
    # HACK: Testing an internal API, but that's fine :)

    # setup mocks
    mock_time_sleep = mock_loop_dependencies(
        mocker, iterations=2, kubernetes_job_status=BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS
    )
    err = Exception("Some error")
    k8s_job_watcher._callback.side_effect = err

    # evaluate
    k8s_job_watcher._thread_run_loop()

    # assertions
    assert k8s_job_watcher._callback.call_count == 1
    assert mock_time_sleep.call_args_list == []
    assert k8s_job_watcher.get_result() == (False, err)


def test_thread_run_loop_when_callback_returns_false_will_not_end_loop(k8s_job_watcher, mocker):
    # HACK: Testing an internal API, but that's fine :)

    mock_time_sleep = mock_loop_dependencies(
        mocker, iterations=2, kubernetes_job_status=BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS
    )
    k8s_job_watcher._callback.return_value = False

    k8s_job_watcher._thread_run_loop()

    assert k8s_job_watcher._callback.call_args_list == [
        call("job-id-1234", BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS),
        call("job-id-1234", BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS),
    ]
    assert mock_time_sleep.call_args_list == [
        call(SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS),
        call(SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS),
    ]
    assert k8s_job_watcher.get_result() == (None, None)
