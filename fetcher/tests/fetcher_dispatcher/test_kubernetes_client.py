import kubernetes

from bai_kafka_utils.events import DataSet

from fetcher_dispatcher import kubernetes_client

from fetcher_dispatcher.args import FetcherJobConfig
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher

from unittest.mock import patch, MagicMock

DATA_SET = DataSet(src="http://some.com/src", dst="s3://bucket/dst/")

ZK_NODE_PATH = "datasets/zk_path"

ZOOKEEPER_ENSEMBLE_HOSTS = "Z1"

FETCHER_JOB_IMAGE = "job/image"

NODE_SELECTOR = {"label1": "val1", "label2": "val2"}

PULL_POLICY = "Never"

FETCHER_JOB_CONFIG = FetcherJobConfig(
    image=FETCHER_JOB_IMAGE, node_selector=NODE_SELECTOR, pull_policy=PULL_POLICY
)

KUBECONFIG = "path/cfg"


@patch.object(kubernetes_client.kubernetes, "config")
@patch.object(kubernetes_client.kubernetes, "client")
def test_kubernetes_init_in_cluster(mock_client, mock_config):
    KubernetesDispatcher(
        zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS,
        kubeconfig=None,
        fetcher_job=FETCHER_JOB_CONFIG,
    )
    mock_config.load_incluster_config.assert_called_once()


@patch.object(kubernetes_client.kubernetes, "config")
@patch.object(kubernetes_client.kubernetes, "client")
def test_kubernetes_init_standalone(mock_client, mock_config):
    KubernetesDispatcher(
        zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS,
        kubeconfig=KUBECONFIG,
        fetcher_job=FETCHER_JOB_CONFIG,
    )
    mock_config.load_kube_config.assert_called_with(KUBECONFIG)


@patch.object(kubernetes_client.kubernetes, "config")
@patch.object(kubernetes_client.kubernetes, "client")
def test_call_dispatcher(mock_client, mock_config):
    kubernetes_dispatcher = KubernetesDispatcher(
        zk_ensemble=ZOOKEEPER_ENSEMBLE_HOSTS,
        kubeconfig=None,
        fetcher_job=FETCHER_JOB_CONFIG,
    )

    mock_client.V1Job = MagicMock(wraps=kubernetes.client.V1Job)
    mock_client.V1PodTemplate = MagicMock(wraps=kubernetes.client.V1PodTemplate)
    mock_client.V1PodTemplate = MagicMock(wraps=kubernetes.client.V1PodTeplateSpec)
    mock_client.V1Container = MagicMock(wraps=kubernetes.client.V1Container)

    kubernetes_dispatcher(DATA_SET, ZK_NODE_PATH)
