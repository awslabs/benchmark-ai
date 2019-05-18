import pytest
from kazoo.client import KazooClient

from bai_kafka_utils.events import BenchmarkEvent, DataSet
from bai_zk_utils.zk_locker import DistributedRWLockManager
from fetcher_dispatcher.args import FetcherServiceConfig
from fetcher_dispatcher.data_set_manager import DataSetManager
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher

EXISTING_DATASET_WITH = "http://files.grouplens.org/datasets/movielens/ml-1m.zip"


@pytest.mark.timeout(60)
def test_fetch(
    fetcher_service_config: FetcherServiceConfig,
    zk_client: KazooClient,
    k8s_dispatcher: KubernetesDispatcher,
    benchmark_event_dummy_payload: BenchmarkEvent,
):
    data_set = DataSet(
        src=EXISTING_DATASET_WITH, dst=f"s3://{fetcher_service_config.s3_data_set_bucket}/it/test.file", md5=None
    )

    locker = DistributedRWLockManager(zk_client, "it_locks")
    data_set_manager = DataSetManager(zk_client, k8s_dispatcher, locker)

    data_set_manager.start()

    test_fetch.test_done = False

    def on_done_test(data_set: DataSet):
        test_fetch.test_done = True

    data_set_manager.fetch(data_set, benchmark_event_dummy_payload, on_done_test)

    while not test_fetch.test_done:
        pass
