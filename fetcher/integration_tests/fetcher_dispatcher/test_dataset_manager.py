import pytest
from kazoo.client import KazooClient
from pytest import fixture

from bai_kafka_utils.events import BenchmarkEvent, DataSet, FetchedType, FetcherStatus
from bai_zk_utils.zk_locker import DistributedRWLockManager
from fetcher_dispatcher.args import FetcherServiceConfig
from fetcher_dispatcher.data_set_manager import DataSetManager
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher

TIMEOUT_FOR_DOWNLOAD_SEC = 30

EXISTING_DATASET = "http://files.grouplens.org/datasets/movielens/ml-1m.zip"

# This will last forever - until we cancel it.
VERY_LARGE_DATASET = "http://files.grouplens.org/datasets/movielens/ml-1m.zip?delay=3600"


@fixture
def data_set_manager(zk_client: KazooClient, k8s_dispatcher: KubernetesDispatcher):
    locker = DistributedRWLockManager(zk_client, "it_locks")
    data_set_manager = DataSetManager(zk_client, k8s_dispatcher, locker)

    data_set_manager.start()
    yield data_set_manager
    data_set_manager.stop()


# Repeat 2 - regression test.
# Checks that unlocking works as expected
@pytest.mark.parametrize("repeat", [1, 2])
@pytest.mark.timeout(TIMEOUT_FOR_DOWNLOAD_SEC)
def test_fetch(
    repeat: int,
    data_set_manager: DataSetManager,
    fetcher_service_config: FetcherServiceConfig,
    benchmark_event_dummy_payload: BenchmarkEvent,
):
    data_sets = []
    for _ in range(repeat):
        data_sets.append(
            DataSet(
                src=EXISTING_DATASET, dst=f"s3://{fetcher_service_config.s3_data_set_bucket}/it/test.file", md5=None
            )
        )

    test_fetch.completed = 0

    def on_done_test(data_set: DataSet):
        assert data_set.src
        assert data_set.type == FetchedType.FILE
        assert data_set.dst
        assert data_set.status == FetcherStatus.DONE

        test_fetch.completed += 1

    for data_set in data_sets:
        data_set_manager.fetch(data_set, benchmark_event_dummy_payload, on_done_test)

    while test_fetch.completed < repeat:
        pass


# This test may be not suitable for real environments
def test_cancel(
    data_set_manager: DataSetManager,
    fetcher_service_config: FetcherServiceConfig,
    benchmark_event_dummy_payload: BenchmarkEvent,
):
    data_set = DataSet(
        src=VERY_LARGE_DATASET, dst=f"s3://{fetcher_service_config.s3_data_set_bucket}/it/test.file", md5=None
    )

    test_fetch.completed = False

    def on_done_test(data_set: DataSet):
        assert data_set.src
        assert data_set.status == FetcherStatus.CANCELED
        assert not data_set.dst

        test_fetch.completed = True

    data_set_manager.fetch(data_set, benchmark_event_dummy_payload, on_done_test)
    data_set_manager.cancel(benchmark_event_dummy_payload.client_id, benchmark_event_dummy_payload.action_id)

    while not test_fetch.completed:
        pass
