from bai_watcher.args import WatcherServiceConfig, get_watcher_service_config

MOCK_KUBECONFIG = "/path/kubeconfig"

KUBERNETES_NAMESPACE = "kubernetes-namespace"

ALL_ARGS = f"--kubernetes-namespace-of-running-jobs={KUBERNETES_NAMESPACE} --kubeconfig={MOCK_KUBECONFIG} "


def test_get_watcher_service_config():
    expected_cfg = WatcherServiceConfig(
        kubernetes_namespace_of_running_jobs=KUBERNETES_NAMESPACE, kubeconfig=MOCK_KUBECONFIG
    )
    cfg = get_watcher_service_config(ALL_ARGS)
    assert cfg == expected_cfg


def test_dont_fail_unrecognized():
    get_watcher_service_config(ALL_ARGS + " -foo")
