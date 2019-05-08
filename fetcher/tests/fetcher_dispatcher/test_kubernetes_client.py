import kubernetes
from kubernetes.client import V1Job
from pytest import fixture
from unittest.mock import patch, MagicMock

from bai_kafka_utils.events import DataSet
from fetcher_dispatcher import kubernetes_client
from fetcher_dispatcher.args import FetcherJobConfig
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher

DATA_SET = DataSet(src="http://some.com/src", dst="s3://bucket/dst/")

ZK_NODE_PATH = "datasets/zk_path"

ZOOKEEPER_ENSEMBLE_HOSTS = "Z1"

FETCHER_JOB_IMAGE = "job/image"

NODE_SELECTOR = {"label1": "val1", "label2": "val2"}

NAMESPACE = "internal"

PULL_POLICY = "OnFailure"

RESTART_POLICY = "OnFailure"

TTL = 42

FETCHER_JOB_CONFIG = FetcherJobConfig(
    namespace=NAMESPACE,
    image=FETCHER_JOB_IMAGE,
    node_selector=NODE_SELECTOR,
    pull_policy=PULL_POLICY,
    ttl=TTL,
    restart_policy=RESTART_POLICY,
)

KUBECONFIG = "path/cfg"


def validate_client_calls(mock_client):
    mock_client.ApiClient.assert_called_once()
    mock_client.BatchV1Api.assert_called_once()


@patch.object(kubernetes_client.kubernetes, "config")
@patch.object(kubernetes_client.kubernetes, "client")
def test_kubernetes_init_in_cluster(mock_client, mock_config):
    KubernetesDispatcher(zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS, kubeconfig=None, fetcher_job=FETCHER_JOB_CONFIG)
    mock_config.load_incluster_config.assert_called_once()
    validate_client_calls(mock_client)


@patch.object(kubernetes_client.kubernetes, "config")
@patch.object(kubernetes_client.kubernetes, "client")
def test_kubernetes_init_standalone(mock_client, mock_config):
    KubernetesDispatcher(zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS, kubeconfig=KUBECONFIG, fetcher_job=FETCHER_JOB_CONFIG)
    mock_config.load_kube_config.assert_called_with(KUBECONFIG)
    validate_client_calls(mock_client)


@fixture
def original_kubernetes_client():
    return kubernetes.client


def validate_namespaced_job(namespace: str, job: V1Job):
    assert namespace == NAMESPACE

    metadata: kubernetes.client.V1ObjectMeta = job.metadata

    assert metadata.namespace == NAMESPACE

    spec: kubernetes.client.V1JobSpec = job.spec

    assert spec.ttl_seconds_after_finished == TTL

    pod_spec: kubernetes.client.V1PodSpec = spec.template.spec

    assert pod_spec.restart_policy == RESTART_POLICY
    assert pod_spec.node_selector == NODE_SELECTOR
    container = pod_spec.containers[0]
    assert container.image_pull_policy == PULL_POLICY
    assert container.image == FETCHER_JOB_IMAGE
    assert container.args == ["--src", DATA_SET.src, "--dst", DATA_SET.dst, "--zk-node-path", ZK_NODE_PATH]
    assert kubernetes.client.V1EnvVar(name="ZOOKEEPER_ENSEMBLE_HOSTS", value=ZOOKEEPER_ENSEMBLE_HOSTS) in container.env


@patch.object(kubernetes_client.kubernetes, "config")
@patch.object(kubernetes_client.kubernetes.client, "BatchV1Api")
def test_call_dispatcher(mockBatchV1Api, mock_config):
    mock_batch_api_instance = MagicMock()

    mockBatchV1Api.return_value = mock_batch_api_instance

    kubernetes_dispatcher = KubernetesDispatcher(
        zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS, kubeconfig=None, fetcher_job=FETCHER_JOB_CONFIG
    )

    kubernetes_dispatcher(DATA_SET, ZK_NODE_PATH)
    mock_batch_api_instance.create_namespaced_job.assert_called_once()

    job_args = mock_batch_api_instance.create_namespaced_job.call_args[0]

    namespace = job_args[0]
    job = job_args[1]

    validate_namespaced_job(namespace, job)
