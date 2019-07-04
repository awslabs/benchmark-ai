import dataclasses

import kubernetes
from bai_kafka_utils.utils import md5sum
from kubernetes.client import V1Job
from pytest import fixture, mark

from bai_k8s_utils.service_labels import ServiceLabels
from bai_kafka_utils.events import DataSet, BenchmarkEvent
from fetcher_dispatcher import kubernetes_dispatcher, SERVICE_NAME
from fetcher_dispatcher.args import FetcherJobConfig, FetcherVolumeConfig
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher
from preflight.data_set_size import DataSetSizeInfo

MB = 1024 * 1024

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
    type="BAI_APP_BFF",
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

SMALL_DATA_SET_SIZE = 1 * MB

MIN_VOLUME_SIZE_MB = 64


SMALL_DATA_SET_SIZE_INFO = DataSetSizeInfo(SMALL_DATA_SET_SIZE, 1, SMALL_DATA_SET_SIZE)
BIG_DATA_SET_SIZE_INFO = DataSetSizeInfo(MIN_VOLUME_SIZE_MB * MB, 1, MIN_VOLUME_SIZE_MB * MB)

FETCHER_JOB_CONFIG = FetcherJobConfig(
    namespace=NAMESPACE,
    image=FETCHER_JOB_IMAGE,
    node_selector=NODE_SELECTOR,
    pull_policy=PULL_POLICY,
    ttl=TTL,
    restart_policy=RESTART_POLICY,
    volume=FetcherVolumeConfig(MIN_VOLUME_SIZE_MB),
)

KUBECONFIG = "path/cfg"


@fixture
def mock_k8s_config(mocker):
    return mocker.patch.object(kubernetes_dispatcher.kubernetes, "config", autospec=True)


@fixture
def mock_k8s_client(mocker):
    # Don't use this fixture with api-mocks
    return mocker.patch.object(kubernetes_dispatcher.kubernetes, "client", autospec=True)


@fixture
def mock_batch_api_instance(mocker) -> kubernetes.client.BatchV1Api:
    mock_api_instance = mocker.create_autospec(kubernetes.client.BatchV1Api)

    mocker.patch.object(
        kubernetes_dispatcher.kubernetes.client, "BatchV1Api", autospec=True, return_value=mock_api_instance
    )

    return mock_api_instance


@fixture
def mock_core_api_instance(mocker) -> kubernetes.client.CoreV1Api:
    mock_api_instance = mocker.create_autospec(kubernetes.client.CoreV1Api)

    mocker.patch.object(
        kubernetes_dispatcher.kubernetes.client, "CoreV1Api", autospec=True, return_value=mock_api_instance
    )

    return mock_api_instance


def test_kubernetes_init_in_cluster(mock_k8s_client, mock_k8s_config):
    KubernetesDispatcher(
        SERVICE_NAME, zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS, kubeconfig=None, fetcher_job=FETCHER_JOB_CONFIG
    )
    mock_k8s_config.load_incluster_config.assert_called_once()
    validate_client_calls(mock_k8s_client)


def validate_client_calls(mock_client):
    mock_client.ApiClient.assert_called_once()
    mock_client.BatchV1Api.assert_called_once()


def test_kubernetes_init_standalone(mock_k8s_client, mock_k8s_config):
    KubernetesDispatcher(
        SERVICE_NAME, zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS, kubeconfig=KUBECONFIG, fetcher_job=FETCHER_JOB_CONFIG
    )
    mock_k8s_config.load_kube_config.assert_called_with(KUBECONFIG)
    validate_client_calls(mock_k8s_client)


@fixture
def original_kubernetes_client():
    return kubernetes.client


@fixture
def k8s_dispatcher(
    mock_k8s_config,
    mock_batch_api_instance: kubernetes.client.BatchV1Api,
    mock_core_api_instance: kubernetes.client.CoreV1Api,
):
    return KubernetesDispatcher(
        SERVICE_NAME, zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS, kubeconfig=None, fetcher_job=FETCHER_JOB_CONFIG
    )


def validate_namespaced_job(namespace: str, job: V1Job, data_set: DataSet):
    assert namespace == NAMESPACE

    metadata: kubernetes.client.V1ObjectMeta = job.metadata

    assert metadata.namespace == NAMESPACE

    assert metadata.labels == {
        ServiceLabels.ACTION_ID_LABEL: ACTION_ID,
        ServiceLabels.CLIENT_ID_LABEL: CLIENT_ID,
        ServiceLabels.CREATED_BY_LABEL: SERVICE_NAME,
        KubernetesDispatcher.DATA_SET_HASH_LABEL: md5sum(data_set.src),
    }

    spec: kubernetes.client.V1JobSpec = job.spec

    assert spec.ttl_seconds_after_finished == TTL

    pod_spec: kubernetes.client.V1PodSpec = spec.template.spec

    assert pod_spec.restart_policy == RESTART_POLICY
    assert pod_spec.node_selector == NODE_SELECTOR
    container: kubernetes.client.V1Container = pod_spec.containers[0]
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

    # We have added the volume for temp files
    assert container.volume_mounts == [
        kubernetes.client.V1VolumeMount(
            mount_path=KubernetesDispatcher.TMP_MOUNT_PATH, name=KubernetesDispatcher.TMP_VOLUME
        )
    ]

    # We passed the ZooKeeper env
    assert (
        kubernetes.client.V1EnvVar(name=KubernetesDispatcher.ZOOKEEPER_ENSEMBLE_HOSTS, value=ZOOKEEPER_ENSEMBLE_HOSTS)
        in container.env
    )
    # We have created a cozy mount for the download
    assert (
        kubernetes.client.V1EnvVar(name=KubernetesDispatcher.TMP_DIR, value=KubernetesDispatcher.TMP_MOUNT_PATH)
        in container.env
    )


@mark.parametrize(
    ["data_set", "size_info"],
    [
        (DATA_SET, SMALL_DATA_SET_SIZE_INFO),
        (DATA_SET_WITH_MD5, SMALL_DATA_SET_SIZE_INFO),
        (DATA_SET, BIG_DATA_SET_SIZE_INFO),
    ],
    ids=["small_no_md5", "small_with_md5", "big_no_md5"],
)
def test_call_dispatcher(
    k8s_dispatcher: KubernetesDispatcher,
    mock_batch_api_instance: kubernetes.client.BatchV1Api,
    mock_core_api_instance: kubernetes.client.CoreV1Api,
    mock_k8s_config,
    data_set: DataSet,
    size_info: DataSetSizeInfo,
):
    k8s_dispatcher.dispatch_fetch(data_set, size_info, BENCHMARK_EVENT, ZK_NODE_PATH)

    mock_batch_api_instance.create_namespaced_job.assert_called_once()

    job_args, _ = mock_batch_api_instance.create_namespaced_job.call_args

    namespace, job = job_args
    validate_namespaced_job(namespace, job, data_set)


def test_cancel_single_action(
    k8s_dispatcher: KubernetesDispatcher,
    mock_batch_api_instance: kubernetes.client.BatchV1Api,
    mock_core_api_instance: kubernetes.client.CoreV1Api,
    mock_k8s_config,
):
    k8s_dispatcher.cancel_all(CLIENT_ID, ACTION_ID)

    _verify_k8s_all_delete(mock_batch_api_instance, mock_core_api_instance)


def test_cleanup(
    k8s_dispatcher: KubernetesDispatcher,
    mock_batch_api_instance: kubernetes.client.BatchV1Api,
    mock_core_api_instance: kubernetes.client.CoreV1Api,
    mock_k8s_config,
):
    k8s_dispatcher.cleanup(DATA_SET, BENCHMARK_EVENT)

    _verify_k8s_all_delete(mock_batch_api_instance, mock_core_api_instance)


def _verify_k8s_all_delete(
    mock_batch_api_instance: kubernetes.client.BatchV1Api, mock_core_api_instance: kubernetes.client.CoreV1Api
):
    mock_batch_api_instance.delete_collection_namespaced_job.assert_called_once()
    mock_core_api_instance.delete_collection_namespaced_pod.assert_called_once()
    mock_core_api_instance.delete_collection_namespaced_persistent_volume_claim.assert_called_once()


def test_cancel_all_actions(
    k8s_dispatcher: KubernetesDispatcher,
    mock_batch_api_instance: kubernetes.client.BatchV1Api,
    mock_core_api_instance: kubernetes.client.CoreV1Api,
    mock_k8s_config,
):
    k8s_dispatcher.cancel_all(CLIENT_ID)

    _verify_k8s_all_delete(mock_batch_api_instance, mock_core_api_instance)


def test_get_label_selector():
    assert (
        KubernetesDispatcher.get_label_selector(SERVICE_NAME, CLIENT_ID, ACTION_ID, DATA_SET)
        == ServiceLabels.get_label_selector(SERVICE_NAME, CLIENT_ID, ACTION_ID)
        + f",{KubernetesDispatcher.DATA_SET_HASH_LABEL}={md5sum(DATA_SET.src)}"
    )
