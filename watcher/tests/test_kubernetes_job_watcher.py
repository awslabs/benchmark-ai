import kubernetes
import pytest
from unittest.mock import Mock, create_autospec, patch, PropertyMock

from bai_watcher.kubernetes_job_watcher import K8SJobWatcher, KubernetesJobStatus
from kubernetes.client import V1Job, V1JobStatus


@pytest.fixture
def fake_kubernetes_client():
    kubernetes_client_fake = create_autospec(kubernetes.client.BatchV1Api)
    return kubernetes_client_fake


def test_k8s_job_watcher(fake_kubernetes_client):
    with patch("bai_watcher.kubernetes_job_watcher.load_kubernetes_config", autospec=True):
        status = create_autospec(V1JobStatus)
        type(status).failed = PropertyMock(return_value=1)
        fake_kubernetes_client.read_namespaced_job_status.return_value = V1Job(status=status)

        callback = Mock()
        k8s_job_watcher = K8SJobWatcher(
            "job-id-1234", callback, kubernetes_namespace="default", kubernetes_client=fake_kubernetes_client
        )
        status = k8s_job_watcher.get_status()
        assert status == KubernetesJobStatus.FAILED
        # callback.assert_called_once_with("job-id-1234", KubernetesJobStatus.FAILED)
