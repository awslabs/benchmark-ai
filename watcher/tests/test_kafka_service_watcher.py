from unittest.mock import call

import kafka
import pytest
from bai_kafka_utils.events import Status, ExecutorBenchmarkEvent, ExecutorPayload, BenchmarkDoc, BenchmarkJob
from bai_kafka_utils.kafka_service import KafkaServiceConfig, KafkaService

from bai_watcher.args import WatcherServiceConfig
from bai_watcher.kafka_service_watcher import create_service, WatchJobsEventHandler, choose_status_from_benchmark_status
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

ACTION_ID = "ACTION_1"
CLIENT_ID = "CLIENT_1"
CONSUMER_TOPIC = "IN_TOPIC"
MOCK_KUBECONFIG = "/path/kubeconfig"
KUBERNETES_NAMESPACE = "kubernetes-namespace"
GRAFANA_ENDPOINT = "grafana-endpoint"
GRAFANA_RESULTS_URL = "{grafana_endpoint}/{dashboard_id}/client_id={client_id}/action_id={action_id}"
GRAFANA_OP_METRICS_DASHBOARD_UID = "op-metrics-uid"
JOB_START_TIME = 1000
JOB_END_TIME = 2000


@pytest.fixture
def k8s_job_watcher(mocker):
    return mocker.patch("bai_watcher.kafka_service_watcher.KubernetesJobWatcher", autospec=True)


@pytest.fixture
def kafka_service_config():
    return KafkaServiceConfig(
        bootstrap_servers=["kafka1:9092", "kafka2:9092"],
        consumer_group_id="GROUP_ID",
        consumer_topic=CONSUMER_TOPIC,
        logging_level="DEBUG",
        producer_topic="OUT_TOPIC",
        status_topic="STATUS_TOPIC",
        cmd_return_topic="CMD_RETURN",
    )


@pytest.fixture(autouse=True)
def kubernetes_config(mocker):
    return mocker.patch("kubernetes.config")


@pytest.fixture
def watcher_service_config():
    return WatcherServiceConfig(
        kubernetes_namespace_of_running_jobs=KUBERNETES_NAMESPACE,
        kubeconfig=MOCK_KUBECONFIG,
        grafana_endpoint=GRAFANA_ENDPOINT,
        grafana_results_url=GRAFANA_RESULTS_URL,
        grafana_op_metrics_dashboard_uid=GRAFANA_OP_METRICS_DASHBOARD_UID,
    )


@pytest.fixture
def kafka_service(mocker, kafka_service_config, watcher_service_config):
    kafka_producer_class = mocker.patch.object(kafka, "KafkaProducer")
    kafka_consumer_class = mocker.patch.object(kafka, "KafkaConsumer")
    _ = mocker.patch(
        "bai_watcher.kafka_service_watcher.create_kafka_consumer_producer",
        return_value=(kafka_consumer_class, kafka_producer_class),
        autospec=True,
    )

    return create_service(kafka_service_config, watcher_service_config)


def test_create_service(mocker, kafka_service_config, watcher_service_config):
    kafka_producer_class = mocker.patch.object(kafka, "KafkaProducer")
    kafka_consumer_class = mocker.patch.object(kafka, "KafkaConsumer")
    mock_create_consumer_producer = mocker.patch(
        "bai_watcher.kafka_service_watcher.create_kafka_consumer_producer",
        return_value=(kafka_consumer_class, kafka_producer_class),
        autospec=True,
    )

    service = create_service(kafka_service_config, watcher_service_config)

    assert isinstance(service, KafkaService)
    mock_create_consumer_producer.assert_called_once()


def test_constructor_loads_kubernetes_config_with_inexistent_kubeconfig_file(kubernetes_config, watcher_service_config):
    watcher_service_config.kubeconfig = "inexistent-path"
    WatchJobsEventHandler(watcher_service_config)
    assert kubernetes_config.load_incluster_config.call_args_list == [call()]
    assert kubernetes_config.load_kube_config.call_args_list == []


def test_constructor_loads_kubernetes_config_with_existing_kubeconfig_file(
    kubernetes_config, datadir, watcher_service_config
):
    kubeconfig_filename = str(datadir / "kubeconfig")
    watcher_service_config.kubeconfig = kubeconfig_filename
    WatchJobsEventHandler(watcher_service_config)
    assert kubernetes_config.load_incluster_config.call_args_list == []
    assert kubernetes_config.load_kube_config.call_args_list == [call(kubeconfig_filename)]


@pytest.mark.parametrize("benchmark_job_status", list(BenchmarkJobStatus))
def test_choose_status_from_benchmark_status(benchmark_job_status):
    status, message = choose_status_from_benchmark_status(benchmark_job_status)
    assert status in list(Status)
    assert message != ""


@pytest.fixture
def benchmark_event():
    return ExecutorBenchmarkEvent(
        action_id=ACTION_ID,
        message_id="MESSAGE_ID",
        client_id=CLIENT_ID,
        client_version="CLIENT_VERSION",
        client_username="CLIENT_USER",
        authenticated=False,
        tstamp=42,
        visited=[],
        type="TYPE",
        payload=ExecutorPayload(
            toml=BenchmarkDoc({"var": "val"}, doc="var=val", sha1="sha"), datasets=[], job=BenchmarkJob(id=ACTION_ID)
        ),
    )


def test_get_metrics_available_message(watcher_service_config, benchmark_event):
    watcher = WatchJobsEventHandler(watcher_service_config)
    message = watcher._get_metrics_available_message(benchmark_event, JOB_START_TIME, JOB_END_TIME)

    expected_grafana_url = GRAFANA_RESULTS_URL.format(
        grafana_endpoint=GRAFANA_ENDPOINT,
        dashboard_id=GRAFANA_OP_METRICS_DASHBOARD_UID,
        client_id=CLIENT_ID,
        action_id=ACTION_ID,
        start_tstamp=JOB_START_TIME,
        end_tstamp=JOB_END_TIME,
    )
    expected_message = watcher.MESSAGE_METRICS_AVAILABLE.format(action_id=ACTION_ID, results_url=expected_grafana_url)

    assert message == expected_message


def test_status_callback_returns_false_on_job_not_found(
    k8s_job_watcher, watcher_service_config, benchmark_event, kafka_service
):
    """
    Checks BenchmarkJobStatus.JOB_DOES_NOT_EXIST makes the status callback return True,
    thus terminating the watcher thread for that job id
    """
    job_id = benchmark_event.payload.job.id

    # setup event handler
    watcher = WatchJobsEventHandler(watcher_service_config)
    watcher.watchers[job_id] = k8s_job_watcher

    # create status callback function
    status_callback = watcher._make_status_callback(benchmark_event, kafka_service)

    assert status_callback(job_id, BenchmarkJobStatus.JOB_DOES_NOT_EXIST, k8s_job_watcher) is True
    assert job_id not in watcher.watchers
