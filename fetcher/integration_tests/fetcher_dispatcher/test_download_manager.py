import pytest
import threading
from kazoo.client import KazooClient
from pytest import fixture
from typing import NamedTuple

from bai_kafka_utils.events import BenchmarkEvent, DownloadableContent, FetchedType, FetcherStatus
from bai_zk_utils.zk_locker import DistributedRWLockManager
from fetcher_dispatcher.args import FetcherServiceConfig
from fetcher_dispatcher.download_manager import DownloadManager
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher
from bai_kafka_utils.integration_tests.test_utils import get_test_timeout

EXISTING_DATASET = "http://files.grouplens.org/datasets/movielens/ml-1m.zip"

# This will last forever - until we cancel it.
VERY_LARGE_DATASET = "http://files.grouplens.org/datasets/movielens/ml-1m.zip?delay=3600"

WAIT_TIMEOUT = get_test_timeout()

DataSetWithEvent = NamedTuple("DataSetWithEvent", [("content", DownloadableContent), ("event", threading.Event)])


@fixture
def download_manager(zk_client: KazooClient, k8s_dispatcher: KubernetesDispatcher):
    locker = DistributedRWLockManager(zk_client, "it_locks")
    download_mgr = DownloadManager(zk_client, k8s_dispatcher, locker)

    download_mgr.start()
    yield download_mgr
    download_mgr.stop()


# Repeat 2 - regression test.
# Checks that unlocking works as expected
@pytest.mark.parametrize("repeat", [1, 2])
def test_fetch(
    repeat: int,
    download_manager,
    fetcher_service_config: FetcherServiceConfig,
    benchmark_event_dummy_payload: BenchmarkEvent,
):
    data_sets_with_events = [
        DataSetWithEvent(
            DownloadableContent(
                src=EXISTING_DATASET, dst=f"s3://{fetcher_service_config.s3_download_bucket}/it/test.file", md5=None
            ),
            threading.Event(),
        )
    ]

    def on_done_test(content: DownloadableContent, completed: threading.Event):
        assert content.src
        assert content.type == FetchedType.FILE
        assert content.dst
        assert content.status == FetcherStatus.DONE
        completed.set()

    for data_sets_with_event in data_sets_with_events:
        download_manager.fetch(
            data_sets_with_event.data_set,
            benchmark_event_dummy_payload,
            lambda d: on_done_test(d, data_sets_with_event.event),
        )

    for _, event in data_sets_with_events:
        event.wait(WAIT_TIMEOUT)


# This test may be not suitable for real environments
# http://files.grouplens.org/datasets/movielens/ml-1m.zip?delay=3600 simulates a one hour download.
# We just want the dataset not to be completed on it's own between fetch and cancel.
# Otherwise it can get a brittle test.
def test_cancel(
    download_manager, fetcher_service_config: FetcherServiceConfig, benchmark_event_dummy_payload: BenchmarkEvent
):
    data_set = DownloadableContent(
        src=VERY_LARGE_DATASET, dst=f"s3://{fetcher_service_config.s3_download_bucket}/it/test.file", md5=None
    )

    completed = threading.Event()

    def on_done_test(content: DownloadableContent):
        assert content.src
        assert content.status == FetcherStatus.CANCELED
        assert not content.dst

        completed.set()

    download_manager.fetch(data_set, benchmark_event_dummy_payload, on_done_test)
    download_manager.cancel(benchmark_event_dummy_payload.client_id, benchmark_event_dummy_payload.action_id)

    assert completed.wait(WAIT_TIMEOUT)
