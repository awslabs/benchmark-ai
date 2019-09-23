import kubernetes
import pytest
from unittest.mock import Mock, create_autospec, call, MagicMock

from bai_watcher.kubernetes_job_watcher import KubernetesJobWatcher, SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS

from bai_watcher.status_inferrers.status import BenchmarkJobStatus
from bai_watcher.status_inferrers.single_node import SingleNodeStrategyKubernetesStatusInferrer


JOB_START_TIME = 1000


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
    assert k8s_job_watcher.get_status() == BenchmarkJobStatus.JOB_NOT_FOUND


@pytest.mark.parametrize("error_code", [500, 503])
def test_get_status_when_kubernetes_raises_a_server_error(k8s_job_watcher, error_code):
    k8s_job_watcher.jobs_client.read_namespaced_job_status.side_effect = kubernetes.client.rest.ApiException(
        status=error_code
    )
    with pytest.raises(kubernetes.client.rest.ApiException) as e:
        k8s_job_watcher.get_status()
    assert e.value.status == error_code


def test_thread_run_loop_when_callback_returns_true_will_end_loop(k8s_job_watcher, mocker):
    # HACK: Testing an internal API, but that's fine :)

    # setup mocks
    mock_time_sleep = mock_loop_dependencies(
        mocker, iterations=2, kubernetes_job_status=BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS
    )
    k8s_job_watcher.callback.return_value = True

    # evaluate
    k8s_job_watcher._thread_run_loop()

    # assertions
    assert k8s_job_watcher.callback.call_args_list == [
        call("job-id-1234", BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS, k8s_job_watcher)
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
    k8s_job_watcher.callback.side_effect = err

    # evaluate
    k8s_job_watcher._thread_run_loop()

    # assertions
    assert k8s_job_watcher.callback.call_args_list == [
        call("job-id-1234", BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS, k8s_job_watcher)
    ]
    assert mock_time_sleep.call_args_list == []
    assert k8s_job_watcher.get_result() == (False, err)


def test_thread_run_loop_when_callback_returns_false_will_not_end_loop(k8s_job_watcher, mocker):
    # HACK: Testing an internal API, but that's fine :)

    mock_time_sleep = mock_loop_dependencies(
        mocker, iterations=2, kubernetes_job_status=BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS
    )
    k8s_job_watcher.callback.return_value = False

    k8s_job_watcher._thread_run_loop()

    assert k8s_job_watcher.callback.call_args_list == [
        call("job-id-1234", BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS, k8s_job_watcher),
        call("job-id-1234", BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS, k8s_job_watcher),
    ]
    assert mock_time_sleep.call_args_list == [
        call(SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS),
        call(SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS),
    ]
    assert k8s_job_watcher.get_result() == (None, None)
