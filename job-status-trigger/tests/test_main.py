import os
from unittest.mock import ANY, call, create_autospec

import pytest
from bai_watcher.status_inferrers.status import BenchmarkJobStatus
from pytest import fixture
from pytest_cases import pytest_parametrize_plus, pytest_fixture_plus, fixture_ref

from bai_job_status_trigger.__main__ import main, make_trigger_callback, get_kubernetes_api_clients

KUBECONFIG = "path/to/kubeconfig"

JOB_NAMESPACE = "namespace"
JOB_NAME = "job_name"
TRIGGER_STATUSES = "[SUCCEEDED, FAILED]"
JOB_NOT_FOUND_GRACE_PERIOD_SECONDS = "30"
COMMAND = "command"


@fixture
def mock_good_env(mocker):
    return mocker.patch.dict(
        os.environ,
        {
            "JOB_NAMESPACE": JOB_NAMESPACE,
            "JOB_NAME": JOB_NAME,
            "TRIGGER_STATUSES": TRIGGER_STATUSES,
            "JOB_NOT_FOUND_GRACE_PERIOD_SECONDS": JOB_NOT_FOUND_GRACE_PERIOD_SECONDS,
            "COMMAND": COMMAND,
        },
        clear=True,
    )


@fixture
def mock_api_client():
    return create_autospec("bai_job_status_trigger.__main__.ApiClient")


@fixture
def mock_batch_api(mocker):
    return mocker.patch("bai_job_status_trigger.__main__.BatchV1Api", auto_spec=True).return_value


@fixture
def mock_core_api(mocker):
    return mocker.patch("bai_job_status_trigger.__main__.CoreV1Api", auto_spec=True).return_value


@fixture
def mock_load_kubernetes_config(mocker):
    return mocker.patch("bai_job_status_trigger.__main__.load_kubernetes_config")


@fixture
def mock_kubernetes_client_configuration():
    return create_autospec("bai_job_status_trigger.__main__.kubernetes.client.Configuration")


@fixture
def mock_empty_env(mocker):
    return mocker.patch.dict(os.environ, {}, clear=True)


@fixture
def mock_kubeconfig_env(mocker):
    return mocker.patch.dict(os.environ, {"KUBECONFIG": KUBECONFIG, "BOB": "hello"}, clear=True)


@fixture
def mock_kubernetes_job_matcher():
    return create_autospec("bai_job_status_trigger.__main__.KubernetesJobWatcher").return_value


@fixture
def mock_kubernetes_job_matcher_class(mocker, mock_kubernetes_job_matcher):
    return mocker.patch(
        "bai_job_status_trigger.__main__.KubernetesJobWatcher", auto_spec=True, return_value=mock_kubernetes_job_matcher
    )


@fixture
def mock_setup_kubernetes_apis(mocker, mock_core_api, mock_batch_api):
    return mocker.patch(
        "bai_job_status_trigger.__main__.setup_kubernetes_apis", return_value=(mock_core_api, mock_batch_api)
    )


@fixture
def mock_check_output(mocker):
    return mocker.patch("bai_job_status_trigger.__main__.check_output")


@pytest_fixture_plus
@pytest_parametrize_plus(
    "env,expected_cfg", [(fixture_ref(mock_kubeconfig_env), KUBECONFIG), (fixture_ref(mock_empty_env), None)]
)
def test_get_kubernetes_api_clients(
    mock_load_kubernetes_config,
    mock_api_client,
    mock_core_api,
    mock_batch_api,
    mock_kubernetes_client_configuration,
    env,
    expected_cfg,
):
    corev1_api, batch_v1api = get_kubernetes_api_clients()

    # assertions
    assert corev1_api == mock_core_api
    assert batch_v1api == mock_batch_api

    mock_load_kubernetes_config.assert_called_with(expected_cfg)


def test_main_happy_path(
    mock_setup_kubernetes_apis,
    mock_kubernetes_job_matcher_class,
    mock_kubernetes_job_matcher,
    mock_core_api,
    mock_batch_api,
    mock_check_output,
    mock_good_env,
):
    mock_kubernetes_job_matcher.get_result.return_value = (True, None)

    main()

    # assertions
    mock_setup_kubernetes_apis.assert_called_once()

    # Job watcher properly initialised
    assert mock_kubernetes_job_matcher_class.call_args_list == [
        call(
            job_id=JOB_NAME,
            callback=ANY,
            kubernetes_namespace=JOB_NAMESPACE,
            kubernetes_client_jobs=mock_batch_api,
            kubernetes_client_pods=mock_core_api,
        )
    ]
    mock_kubernetes_job_matcher.start.assert_called_once()
    mock_kubernetes_job_matcher.wait.assert_called_once()

    assert mock_check_output.call_args_list == [call(["bash", "-c", COMMAND])]


def test_main_error(
    mock_setup_kubernetes_apis,
    mock_kubernetes_job_matcher_class,
    mock_kubernetes_job_matcher,
    mock_core_api,
    mock_batch_api,
    mock_check_output,
    mock_good_env,
):
    mock_kubernetes_job_matcher.get_result.return_value = (False, Exception("some error"))

    with pytest.raises(SystemExit):
        main()

    # assertions
    # nothing is executed
    mock_check_output.assert_not_called()


@pytest.mark.parametrize(
    "trigger_statuses,job_status,not_found_grace_period,expected",
    [
        ([BenchmarkJobStatus.SUCCEEDED], BenchmarkJobStatus.SUCCEEDED, 30, True),
        ([BenchmarkJobStatus.SUCCEEDED], BenchmarkJobStatus.FAILED, 30, False),
    ],
)
def test_trigger_callback(trigger_statuses, job_status, not_found_grace_period, expected):
    fn = make_trigger_callback(trigger_statuses, not_found_grace_period)
    assert fn(JOB_NAME, job_status, None) is expected


def test_trigger_callback_fails_on_job_disappears_if_not_found_not_in_trigger_statuses():
    fn = make_trigger_callback([BenchmarkJobStatus.SUCCEEDED], 30)
    assert fn(JOB_NAME, BenchmarkJobStatus.JOB_NOT_FOUND, None) is False
    assert fn(JOB_NAME, BenchmarkJobStatus.PENDING_NODE_SCALING, None) is False
    with pytest.raises(RuntimeError):
        fn(JOB_NAME, BenchmarkJobStatus.JOB_NOT_FOUND, None)


def test_trigger_callback_success_on_job_disappears_if_not_found_in_trigger_statuses():
    fn = make_trigger_callback([BenchmarkJobStatus.SUCCEEDED, BenchmarkJobStatus.JOB_NOT_FOUND], 30)
    assert fn(JOB_NAME, BenchmarkJobStatus.JOB_NOT_FOUND, None) is False
    assert fn(JOB_NAME, BenchmarkJobStatus.PENDING_NODE_SCALING, None) is False
    assert fn(JOB_NAME, BenchmarkJobStatus.JOB_NOT_FOUND, None) is True


def test_not_found_after_grace_period_raises(mocker):
    mock_time = mocker.patch("bai_job_status_trigger.__main__.time")

    mock_time.side_effect = [0, 5, 35]

    fn = make_trigger_callback([BenchmarkJobStatus.SUCCEEDED, BenchmarkJobStatus.JOB_NOT_FOUND], 30)
    assert fn(JOB_NAME, BenchmarkJobStatus.JOB_NOT_FOUND, None) is False

    # job has not been found within grace period
    with pytest.raises(RuntimeError):
        fn(JOB_NAME, BenchmarkJobStatus.JOB_NOT_FOUND, None)
