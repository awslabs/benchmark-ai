from bai_watcher.args import WatcherServiceConfig, get_watcher_service_config

MOCK_KUBECONFIG = "/path/kubeconfig"
KUBERNETES_NAMESPACE = "kubernetes-namespace"
GRAFANA_ENDPOINT = "grafana-endpoint"
GRAFANA_RESULTS_URL = "grafana-results"
GRAFANA_OP_METRICS_DASHBOARD_UID = "op-metrics-uid"

ALL_ARGS = (
    f" --kubernetes-namespace-of-running-jobs={KUBERNETES_NAMESPACE}"
    f" --kubeconfig={MOCK_KUBECONFIG} "
    f" --grafana-endpoint={GRAFANA_ENDPOINT}"
    f" --grafana-results-url={GRAFANA_RESULTS_URL}"
    f" --grafana-op-metrics-dashboard-uid={GRAFANA_OP_METRICS_DASHBOARD_UID}"
)


def test_get_watcher_service_config():
    expected_cfg = WatcherServiceConfig(
        kubernetes_namespace_of_running_jobs=KUBERNETES_NAMESPACE,
        kubeconfig=MOCK_KUBECONFIG,
        grafana_endpoint=GRAFANA_ENDPOINT,
        grafana_results_url=GRAFANA_RESULTS_URL,
        grafana_op_metrics_dashboard_uid=GRAFANA_OP_METRICS_DASHBOARD_UID,
    )
    cfg = get_watcher_service_config(ALL_ARGS)
    assert cfg == expected_cfg


def test_dont_fail_unrecognized():
    get_watcher_service_config(ALL_ARGS + " -foo")
