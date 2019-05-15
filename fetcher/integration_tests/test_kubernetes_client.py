import os

from pytest import fixture

from bai_kafka_utils.events import DataSet, BenchmarkEvent
from fetcher_dispatcher.args import FetcherJobConfig
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher


@fixture
def fetcher_job_config():
    return FetcherJobConfig(
        image="stsukrov/mock-fetcher-job",
        pull_policy="Never",
        node_selector={},
        namespace="default",
        restart_policy="Never",
    )


BENCHMARK_EVENT = BenchmarkEvent(
    action_id="ACTION_ID",
    message_id="DONTCARE",
    client_id="CLIENT_ID",
    client_version="DONTCARE",
    client_username="DONTCARE",
    authenticated=False,
    tstamp=42,
    visited=[],
    payload="DONTCARE",
)


def test_kuberenetes_client(fetcher_job_config):
    kubeconfig = os.environ["KUBECONFIG"]
    zk_ensemble = os.environ["ZOOKEEPER_ENSEMBLE_HOSTS"]
    k8s_dispatcher = KubernetesDispatcher(kubeconfig, zk_ensemble, fetcher_job_config)

    data_set = DataSet(src="http://somedata.big", dst="s3://dst", md5=None)

    k8s_dispatcher(data_set, BENCHMARK_EVENT, "/data/sets/fake")
