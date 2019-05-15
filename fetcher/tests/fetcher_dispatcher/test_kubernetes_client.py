import dataclasses

import kubernetes
from kubernetes.client import V1Job
from pytest import fixture, mark

from bai_kafka_utils.events import DataSet, BenchmarkEvent
from fetcher_dispatcher import kubernetes_client

from fetcher_dispatcher.args import FetcherJobConfig
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher

CLIENT_ID = "CLIENT_ID"

ACTION_ID = "ACTION_ID"

DATA_SET = DataSet(src="http://some.com/src", dst="s3://bucket/dst/")
DATA_SET_WITH_MD5 = dataclasses.replace(DATA_SET, md5="42")

BENCHMARK_EVENT = BenchmarkEvent(
    action_id=ACTION_ID,
    message_id="DONTCARE",
    client_id=CLIENT_ID,
    client_version="DONTCARE",
    client_username="DONTCARE",
    authenticated=False,
    tstamp=42,
    visited=[],
    payload="DONTCARE",
)

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


@fixture
def mock_k8s_config(mocker):
    return mocker.patch.object(kubernetes_client.kubernetes, "config", autospec=True)


@fixture
def mock_k8s_client(mocker):
    return mocker.patch.object(kubernetes_client.kubernetes, "client", autospec=True)


@fixture
def mock_api_instance(mocker):
    mock_batch_api_instance = mocker.create_autospec(kubernetes.client.BatchV1Api)

    mocker.patch.object(
        kubernetes_client.kubernetes.client, "BatchV1Api", autospec=True, return_value=mock_batch_api_instance
    )

    return mock_batch_api_instance


def test_kubernetes_init_in_cluster(mock_k8s_client, mock_k8s_config):
    KubernetesDispatcher(zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS, kubeconfig=None, fetcher_job=FETCHER_JOB_CONFIG)
    mock_k8s_config.load_incluster_config.assert_called_once()
    validate_client_calls(mock_k8s_client)


def test_kubernetes_init_standalone(mock_k8s_client, mock_k8s_config):
    KubernetesDispatcher(zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS, kubeconfig=KUBECONFIG, fetcher_job=FETCHER_JOB_CONFIG)
    mock_k8s_config.load_kube_config.assert_called_with(KUBECONFIG)
    validate_client_calls(mock_k8s_client)


@fixture
def original_kubernetes_client():
    return kubernetes.client


def validate_namespaced_job(namespace: str, job: V1Job, data_set: DataSet):
    assert namespace == NAMESPACE

    metadata: kubernetes.client.V1ObjectMeta = job.metadata

    assert metadata.namespace == NAMESPACE

    assert metadata.labels == {
        KubernetesDispatcher.ACTION_ID_LABEL: ACTION_ID,
        KubernetesDispatcher.CLIENT_ID_LABEL: CLIENT_ID,
    }

    spec: kubernetes.client.V1JobSpec = job.spec

    assert spec.ttl_seconds_after_finished == TTL

    pod_spec: kubernetes.client.V1PodSpec = spec.template.spec

    assert pod_spec.restart_policy == RESTART_POLICY
    assert pod_spec.node_selector == NODE_SELECTOR
    container = pod_spec.containers[0]
    assert container.image_pull_policy == PULL_POLICY
    assert container.image == FETCHER_JOB_IMAGE

    assert container.args == [
        KubernetesDispatcher.SRC_ARG,
        DATA_SET.src,
        KubernetesDispatcher.DST_ARG,
        DATA_SET.dst,
        KubernetesDispatcher.ZK_NODE_PATH_ARG,
        ZK_NODE_PATH,
        KubernetesDispatcher.MD5_ARG,
        data_set.md5,
    ]
    assert (
        kubernetes.client.V1EnvVar(name=KubernetesDispatcher.ZOOKEEPER_ENSEMBLE_HOSTS, value=ZOOKEEPER_ENSEMBLE_HOSTS)
        in container.env
    )


@mark.parametrize("data_set", [DATA_SET, DATA_SET_WITH_MD5])
def test_call_dispatcher(mock_api_instance, mock_k8s_config, data_set):
    kubernetes_dispatcher = KubernetesDispatcher(
        zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS, kubeconfig=None, fetcher_job=FETCHER_JOB_CONFIG
    )

    kubernetes_dispatcher(data_set, BENCHMARK_EVENT, ZK_NODE_PATH)
    mock_api_instance.create_namespaced_job.assert_called_once()

    job_args, _ = mock_api_instance.create_namespaced_job.call_args

    namespace = job_args[0]
    job = job_args[1]

    validate_namespaced_job(namespace, job, data_set)
