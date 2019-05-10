import kubernetes
import pytest
from unittest.mock import Mock, create_autospec, PropertyMock, call

from bai_watcher.kubernetes_job_watcher import (
    KubernetesJobWatcher,
    KubernetesJobStatus,
    SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS,
)
from kubernetes.client import V1Job, V1JobStatus


def mock_job_status(kubernetes_client, kubernetes_job_status: KubernetesJobStatus):
    k8s_job_status = create_autospec(V1JobStatus)
    value = PropertyMock(return_value=1)
    if kubernetes_job_status == KubernetesJobStatus.FAILED:
        type(k8s_job_status).failed = value
    elif kubernetes_job_status == KubernetesJobStatus.SUCCEEDED:
        type(k8s_job_status).succeeded = value
    elif kubernetes_job_status == KubernetesJobStatus.RUNNING:
        type(k8s_job_status).active = value
    kubernetes_client.read_namespaced_job_status.return_value = V1Job(status=k8s_job_status)


def create_fake_kubernetes_client(mocker) -> kubernetes.client.BatchV1Api:
    mocker.patch("bai_watcher.kubernetes_job_watcher.load_kubernetes_config", autospec=True)
    fake_kubernetes_client = create_autospec(kubernetes.client.BatchV1Api)
    return fake_kubernetes_client


@pytest.fixture
def k8s_job_watcher(mocker):

    return KubernetesJobWatcher(
        "job-id-1234", Mock(), kubernetes_namespace="default", kubernetes_client=create_fake_kubernetes_client(mocker)
    )


@pytest.mark.parametrize("status", list(KubernetesJobStatus))
def test_get_status(k8s_job_watcher, status):
    mock_job_status(k8s_job_watcher.kubernetes_client, status)
    assert k8s_job_watcher.get_status() == status


def test_get_status_when_job_does_not_exist(k8s_job_watcher):
    k8s_job_watcher.kubernetes_client.read_namespaced_job_status.side_effect = kubernetes.client.rest.ApiException(
        status=404
    )
    assert k8s_job_watcher.get_status() is None


@pytest.mark.parametrize("error_code", [500, 503])
def test_get_status_when_kubernetes_raises_a_server_error(k8s_job_watcher, error_code):
    k8s_job_watcher.kubernetes_client.read_namespaced_job_status.side_effect = kubernetes.client.rest.ApiException(
        status=error_code
    )
    with pytest.raises(kubernetes.client.rest.ApiException) as e:
        k8s_job_watcher.get_status()
    assert e.value.status == error_code


def test_get_status_when_kubernetes_job_report_from_api_is_buggy(k8s_job_watcher):
    # This tests a situation if we handle Kubernetes returning buggy objects
    k8s_job_status = create_autospec(V1JobStatus)
    value = PropertyMock(return_value=0)
    type(k8s_job_status).failed = value
    type(k8s_job_status).succeeded = value
    type(k8s_job_status).active = value
    k8s_job_watcher.kubernetes_client.read_namespaced_job_status.return_value = V1Job(status=k8s_job_status)
    with pytest.raises(ValueError):
        k8s_job_watcher.get_status()


def test_thread_run_loop_when_callback_returns_true_will_end_loop(k8s_job_watcher, mocker):
    # HACK: Testing an internal API, but that's fine :)

    # setup mocks
    mock_time_sleep = mock_loop_dependencies(
        k8s_job_watcher, mocker, iterations=2, kubernetes_job_status=KubernetesJobStatus.RUNNING
    )
    k8s_job_watcher.callback.return_value = True

    # evaluate
    k8s_job_watcher._thread_run_loop()

    # assertions
    assert k8s_job_watcher.callback.call_args_list == [call("job-id-1234", KubernetesJobStatus.RUNNING)]
    assert mock_time_sleep.call_args_list == []


def test_thread_run_loop_when_callback_returns_false_will_not_end_loop(k8s_job_watcher, mocker):
    # HACK: Testing an internal API, but that's fine :)

    mock_time_sleep = mock_loop_dependencies(
        k8s_job_watcher, mocker, iterations=2, kubernetes_job_status=KubernetesJobStatus.RUNNING
    )
    k8s_job_watcher.callback.return_value = False

    k8s_job_watcher._thread_run_loop()

    assert k8s_job_watcher.callback.call_args_list == [
        call("job-id-1234", KubernetesJobStatus.RUNNING),
        call("job-id-1234", KubernetesJobStatus.RUNNING),
    ]
    assert mock_time_sleep.call_args_list == [
        call(SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS),
        call(SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS),
    ]


def mock_loop_dependencies(k8s_job_watcher, mocker, *, iterations, kubernetes_job_status):
    mocker.patch("itertools.count", return_value=[0] * iterations)  # 2 iterations
    mock_time_sleep = mocker.patch("time.sleep")
    mock_job_status(k8s_job_watcher.kubernetes_client, kubernetes_job_status)
    return mock_time_sleep
