import os
import yaml
import pytest

from pytest import fixture
from unittest.mock import MagicMock, call

from kubernetes.client import V1Pod, V1PodStatus, V1ObjectMeta
from kubernetes.client.rest import ApiException

from pathlib import Path

from bai_inference_benchmark.args import InferenceBenchmarkConfig
from bai_inference_benchmark.inference_benchmark import InferenceBenchmark, InferenceBenchmarkFailedError


KUBECONFIG_PATH = "/path/to/kubeconfig"
SERVER_POD_NAME = "server"
CLIENT_POD_NAME = "client"
DEFAULT_NAMESPACE = "default"

# Pod phases
SUCCEEDED = "Succeeded"
PENDING = "Pending"
FAILED = "Failed"
RUNNING = "Running"
UNKNOWN = "Unknown"


@fixture
def inference_benchmark_config(shared_datadir):
    return InferenceBenchmarkConfig(
        benchmark_namespace=DEFAULT_NAMESPACE,
        benchmark_pod_spec=Path(os.path.join(shared_datadir, "client.yaml")),
        server_pod_spec=Path(os.path.join(shared_datadir, "server.yaml")),
    )


@fixture
def kubernetes_config():
    return MagicMock()


@fixture
def kubernetes_client():
    return MagicMock()


@fixture
def mock_api_client(mocker):
    return mocker.patch("bai_inference_benchmark.inference_benchmark.ApiClient", autospec=True).return_value


@fixture
def mock_corev1_api(mocker):
    return mocker.patch("bai_inference_benchmark.inference_benchmark.CoreV1Api", autospec=True).return_value


@fixture
def empty_env(mocker):
    return mocker.patch.dict(os.environ, {}, clear=True)


@fixture
def kubeconfig_env(mocker):
    return mocker.patch.dict(os.environ, {"KUBECONFIG": KUBECONFIG_PATH}, clear=True)


@fixture
def mock_path_not_found(mocker):
    mock = mocker.patch("bai_inference_benchmark.inference_benchmark.Path", autospec=True)
    mock.return_value.exists.return_value = False
    return mock


@fixture
def mock_path_found(mocker):
    mock = mocker.patch("bai_inference_benchmark.inference_benchmark.Path", autospec=True)
    mock.return_value.exists.return_value = True
    mock.home.return_value = Path.home()
    return mock


@fixture
def mock_kubernetes(mocker, mock_api_client, kubernetes_config, kubernetes_client):
    kubernetes_mock = mocker.patch("bai_inference_benchmark.inference_benchmark.kubernetes")
    kubernetes_mock.config.return_value = kubernetes_config
    kubernetes_mock.client.return_value = kubernetes_client
    return kubernetes_mock


def fake_v1pod(namespace: str, name: str, phase: str) -> V1Pod:
    pod = V1Pod(kind="Pod", metadata=V1ObjectMeta(namespace=namespace, name=name), status=V1PodStatus(phase=phase))
    return pod


def server_pod_with_phase(phase: str):
    return fake_v1pod(namespace=DEFAULT_NAMESPACE, name=SERVER_POD_NAME, phase=phase)


def benchmark_pod_with_phase(phase: str):
    return fake_v1pod(namespace=DEFAULT_NAMESPACE, name=CLIENT_POD_NAME, phase=phase)


def deserialize_yaml(yaml_path: Path):
    with open(str(yaml_path)) as f:
        return yaml.safe_load(f)


def mock_loop_dependencies(mocker, *, max_iterations):
    mocker.patch("itertools.count", return_value=[0] * max_iterations)
    mock_time_sleep = mocker.patch("time.sleep")
    return mock_time_sleep


def test_load_incluster_config(
    empty_env,  # No KUBECONFIG in environment
    mock_path_not_found,  # Path to ~/.kube/config not found
    mock_kubernetes,  # mock kubernetes library
    inference_benchmark_config,
):
    """
    Tests load_incluser_config is called when KUBECONFIG env var absent and ~/.kube/config does not exist
    """
    InferenceBenchmark(inference_benchmark_config)
    mock_kubernetes.config.load_incluster_config.assert_called_once()


def test_load_kubeconfig_env_var(
    kubeconfig_env,  # KUBECONFIG in environment
    mock_path_found,  # Path to ${KUBECONFIG} exists
    mock_kubernetes,  # mock kubernetes library
    inference_benchmark_config,
):
    """
    Tests kubernetes configuration is loaded from ${KUBECONFIG}
    """
    InferenceBenchmark(inference_benchmark_config)
    mock_path_found.assert_called_with(KUBECONFIG_PATH)
    mock_kubernetes.config.load_kube_config.assert_called_once()


def test_load_kubeconfig_home_kube_config(
    empty_env,  # No KUBECONFIG in environment
    mock_path_found,  # Path to ~/.kube/config exists
    mock_kubernetes,  # mock kubernetes library
    inference_benchmark_config,
):
    """
    Tests kubernetes configuration is loaded from ~/.kube/config
    """
    InferenceBenchmark(inference_benchmark_config)
    mock_path_found.assert_called_with(Path.home().joinpath(".kube", "config"))
    mock_kubernetes.config.load_kube_config.assert_called_once()


def test_execute_happy_path(
    mocker, mock_kubernetes, mock_corev1_api, inference_benchmark_config: InferenceBenchmarkConfig
):

    # ensure we don't end up in an infinite loop
    mock_sleep = mock_loop_dependencies(mocker, max_iterations=2)

    # pod creation - order matters
    mock_corev1_api.create_namespaced_pod.side_effect = [
        server_pod_with_phase(SUCCEEDED),
        benchmark_pod_with_phase(SUCCEEDED),
    ]

    # pod status - order matters
    mock_corev1_api.read_namespaced_pod_status.side_effect = [
        server_pod_with_phase(SUCCEEDED),
        benchmark_pod_with_phase(SUCCEEDED),
    ]

    # Run benchmark
    InferenceBenchmark(inference_benchmark_config).execute()

    # Creates pods
    mock_corev1_api.create_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.benchmark_pod_spec)),
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.server_pod_spec)),
        ],
        any_order=True,
    )

    # Deletes pods at the end
    mock_corev1_api.delete_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, name=SERVER_POD_NAME, grace_period_seconds=0),
            call(namespace=DEFAULT_NAMESPACE, name=CLIENT_POD_NAME, grace_period_seconds=0),
        ],
        any_order=True,
    )

    assert mock_sleep.mock_calls == []


def test_execute_benchmark_ends_successfully(
    mocker, mock_kubernetes, mock_corev1_api, inference_benchmark_config: InferenceBenchmarkConfig
):
    """
    Tests benchmark waits for benchmark pod completion
    """
    # ensure we don't end up in an infinite loop
    mock_sleep = mock_loop_dependencies(mocker, max_iterations=20)

    # pod creation - order matters
    mock_corev1_api.create_namespaced_pod.side_effect = [
        server_pod_with_phase(PENDING),
        benchmark_pod_with_phase(PENDING),
    ]

    # pod status - order matters
    mock_corev1_api.read_namespaced_pod_status.side_effect = (
        [server_pod_with_phase(PENDING), benchmark_pod_with_phase(PENDING)] * 2
        + [server_pod_with_phase(RUNNING), benchmark_pod_with_phase(PENDING)] * 2
        + [server_pod_with_phase(RUNNING), benchmark_pod_with_phase(RUNNING)]
        + [server_pod_with_phase(RUNNING), benchmark_pod_with_phase(SUCCEEDED)]
    )

    # Run benchmark
    InferenceBenchmark(inference_benchmark_config).execute()

    # Creates pods
    mock_corev1_api.create_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.benchmark_pod_spec)),
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.server_pod_spec)),
        ],
        any_order=True,
    )

    # Deletes pods at the end
    mock_corev1_api.delete_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, name=SERVER_POD_NAME, grace_period_seconds=0),
            call(namespace=DEFAULT_NAMESPACE, name=CLIENT_POD_NAME, grace_period_seconds=0),
        ],
        any_order=True,
    )

    assert mock_sleep.call_count == 5


@pytest.mark.parametrize("server_pod_final_phase", [SUCCEEDED, FAILED, UNKNOWN])
def test_execute_server_ends_successfully_fails(
    mocker,
    mock_kubernetes,
    mock_corev1_api,
    inference_benchmark_config: InferenceBenchmarkConfig,
    server_pod_final_phase: str,
):
    """
    Tests benchmark fails if server pods enters a final state
    """
    # ensure we don't end up in an infinite loop
    mock_sleep = mock_loop_dependencies(mocker, max_iterations=20)

    # pod creation - order matters
    mock_corev1_api.create_namespaced_pod.side_effect = [
        server_pod_with_phase(PENDING),
        benchmark_pod_with_phase(PENDING),
    ]

    # pod status - order matters
    mock_corev1_api.read_namespaced_pod_status.side_effect = (
        [server_pod_with_phase(PENDING), benchmark_pod_with_phase(PENDING)] * 2
        + [server_pod_with_phase(RUNNING), benchmark_pod_with_phase(PENDING)] * 2
        + [server_pod_with_phase(RUNNING), benchmark_pod_with_phase(RUNNING)]
        + [server_pod_with_phase(server_pod_final_phase), benchmark_pod_with_phase(RUNNING)]
    )

    # Run benchmark
    with pytest.raises(InferenceBenchmarkFailedError):
        InferenceBenchmark(inference_benchmark_config).execute()

    # Creates pods
    mock_corev1_api.create_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.benchmark_pod_spec)),
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.server_pod_spec)),
        ],
        any_order=True,
    )

    # Deletes pods at the end
    mock_corev1_api.delete_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, name=SERVER_POD_NAME, grace_period_seconds=0),
            call(namespace=DEFAULT_NAMESPACE, name=CLIENT_POD_NAME, grace_period_seconds=0),
        ],
        any_order=True,
    )

    assert mock_sleep.call_count == 5


@pytest.mark.parametrize("benchmark_pod_final_phase", [FAILED, UNKNOWN])
def test_execute_benchmark_ends_unsuccessfully_fails(
    mocker,
    mock_kubernetes,
    mock_corev1_api,
    inference_benchmark_config: InferenceBenchmarkConfig,
    benchmark_pod_final_phase: str,
):
    """
    Tests benchmark fails if benchmark pods enters an unsuccessful final state
    """
    # ensure we don't end up in an infinite loop
    mock_sleep = mock_loop_dependencies(mocker, max_iterations=20)

    # pod creation - order matters
    mock_corev1_api.create_namespaced_pod.side_effect = [
        server_pod_with_phase(PENDING),
        benchmark_pod_with_phase(PENDING),
    ]

    # pod status - order matters
    mock_corev1_api.read_namespaced_pod_status.side_effect = (
        [server_pod_with_phase(PENDING), benchmark_pod_with_phase(PENDING)] * 2
        + [server_pod_with_phase(RUNNING), benchmark_pod_with_phase(PENDING)] * 2
        + [server_pod_with_phase(RUNNING), benchmark_pod_with_phase(RUNNING)]
        + [server_pod_with_phase(RUNNING), benchmark_pod_with_phase(benchmark_pod_final_phase)]
    )

    # Run benchmark
    with pytest.raises(InferenceBenchmarkFailedError):
        InferenceBenchmark(inference_benchmark_config).execute()

    # Creates pods
    mock_corev1_api.create_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.benchmark_pod_spec)),
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.server_pod_spec)),
        ],
        any_order=True,
    )

    # Deletes pods at the end
    mock_corev1_api.delete_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, name=SERVER_POD_NAME, grace_period_seconds=0),
            call(namespace=DEFAULT_NAMESPACE, name=CLIENT_POD_NAME, grace_period_seconds=0),
        ],
        any_order=True,
    )

    assert mock_sleep.call_count == 5


def test_execute_benchmark_status_not_found_fails(
    mocker, mock_kubernetes, mock_corev1_api, inference_benchmark_config: InferenceBenchmarkConfig
):
    """
    Tests benchmark fails if benchmark pods is not found
    """
    # ensure we don't end up in an infinite loop
    mock_sleep = mock_loop_dependencies(mocker, max_iterations=2)

    # pod creation - order matters
    mock_corev1_api.create_namespaced_pod.side_effect = [
        server_pod_with_phase(PENDING),
        benchmark_pod_with_phase(PENDING),
    ]

    # pod status - order matters
    mock_corev1_api.read_namespaced_pod_status.side_effect = [server_pod_with_phase(PENDING), ApiException(status=404)]

    # Run benchmark
    with pytest.raises(InferenceBenchmarkFailedError):
        InferenceBenchmark(inference_benchmark_config).execute()

    # Creates pods
    mock_corev1_api.create_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.benchmark_pod_spec)),
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.server_pod_spec)),
        ],
        any_order=True,
    )

    # Deletes pods at the end
    mock_corev1_api.delete_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, name=SERVER_POD_NAME, grace_period_seconds=0),
            call(namespace=DEFAULT_NAMESPACE, name=CLIENT_POD_NAME, grace_period_seconds=0),
        ],
        any_order=True,
    )

    mock_sleep.assert_not_called()


def test_execute_server_status_not_found_fails(
    mocker, mock_kubernetes, mock_corev1_api, inference_benchmark_config: InferenceBenchmarkConfig
):
    """
    Tests benchmark fails if server pods is not found
    """
    # ensure we don't end up in an infinite loop
    mock_sleep = mock_loop_dependencies(mocker, max_iterations=2)

    # pod creation - order matters
    mock_corev1_api.create_namespaced_pod.side_effect = [
        server_pod_with_phase(PENDING),
        benchmark_pod_with_phase(PENDING),
    ]

    # pod status - order matters
    mock_corev1_api.read_namespaced_pod_status.side_effect = [
        ApiException(status=404),
        benchmark_pod_with_phase(PENDING),
    ]

    # Run benchmark
    with pytest.raises(InferenceBenchmarkFailedError):
        InferenceBenchmark(inference_benchmark_config).execute()

    # Creates pods
    mock_corev1_api.create_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.benchmark_pod_spec)),
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.server_pod_spec)),
        ],
        any_order=True,
    )

    # Deletes pods at the end
    mock_corev1_api.delete_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, name=SERVER_POD_NAME, grace_period_seconds=0),
            call(namespace=DEFAULT_NAMESPACE, name=CLIENT_POD_NAME, grace_period_seconds=0),
        ],
        any_order=True,
    )

    mock_sleep.assert_not_called()


def test_execute_fails_if_cannot_create_benchmark_pod(
    mocker, mock_kubernetes, mock_corev1_api, inference_benchmark_config: InferenceBenchmarkConfig
):
    """
    Tests benchmark fails if benchmark pod cannot be created
    """
    # ensure we don't end up in an infinite loop
    mock_sleep = mock_loop_dependencies(mocker, max_iterations=2)

    # pod creation - order matters
    mock_corev1_api.create_namespaced_pod.side_effect = [server_pod_with_phase(PENDING), ApiException(status=409)]

    # Run benchmark
    with pytest.raises(InferenceBenchmarkFailedError):
        InferenceBenchmark(inference_benchmark_config).execute()

    # Creates pods
    mock_corev1_api.create_namespaced_pod.assert_has_calls(
        [
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.benchmark_pod_spec)),
            call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.server_pod_spec)),
        ],
        any_order=True,
    )

    # Deletes server pod at the end
    mock_corev1_api.delete_namespaced_pod.assert_has_calls(
        [call(namespace=DEFAULT_NAMESPACE, name=SERVER_POD_NAME, grace_period_seconds=0)], any_order=True
    )

    mock_sleep.assert_not_called()


def test_execute_fails_if_cannot_create_server_pod(
    mocker, mock_kubernetes, mock_corev1_api, inference_benchmark_config: InferenceBenchmarkConfig
):
    """
    Tests benchmark fails if server pod cannot be created
    """
    # ensure we don't end up in an infinite loop
    mock_sleep = mock_loop_dependencies(mocker, max_iterations=2)

    # pod creation - order matters
    mock_corev1_api.create_namespaced_pod.side_effect = [ApiException(status=409), benchmark_pod_with_phase(PENDING)]

    # Run benchmark
    with pytest.raises(InferenceBenchmarkFailedError):
        InferenceBenchmark(inference_benchmark_config).execute()

    # Tries to create server pod
    mock_corev1_api.create_namespaced_pod.assert_has_calls(
        [call(namespace=DEFAULT_NAMESPACE, body=deserialize_yaml(inference_benchmark_config.server_pod_spec))],
        any_order=True,
    )

    # No pods were created, so nothing to delete
    mock_corev1_api.delete_namespaced_pod.assert_not_called()
    mock_sleep.assert_not_called()
