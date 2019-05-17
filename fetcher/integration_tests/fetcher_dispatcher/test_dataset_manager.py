import pytest
from kazoo.client import KazooClient

from bai_kafka_utils.events import BenchmarkEvent, DataSet
from bai_zk_utils.zk_locker import DistributedRWLockManager
from fetcher_dispatcher.args import FetcherServiceConfig
from fetcher_dispatcher.data_set_manager import DataSetManager
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher

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


@pytest.mark.timeout(60)
def test_fetch(
    fetcher_service_config: FetcherServiceConfig, zk_client: KazooClient, k8s_dispatcher: KubernetesDispatcher
):

    data_set = DataSet(src="http://somedata.big", dst="s3://dst", md5=None)

    locker = DistributedRWLockManager(zk_client, "it_locks")
    data_set_manager = DataSetManager(zk_client, k8s_dispatcher, locker)

    data_set_manager.start()

    test_fetch.test_done = False

    def on_done_test(data_set: DataSet):
        test_fetch.test_done = True

    data_set_manager.fetch(data_set, BENCHMARK_EVENT, on_done_test)

    while not test_fetch.test_done:
        pass
