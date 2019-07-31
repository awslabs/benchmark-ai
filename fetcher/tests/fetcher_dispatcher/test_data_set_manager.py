from unittest import mock

import kazoo

from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError, BadVersionError
from kazoo.protocol.states import WatchedEvent, EventType, KeeperState, ZnodeStat
from pytest import fixture
from typing import Any
from unittest.mock import create_autospec

from bai_io_utils.failures import UnRetryableError
from bai_kafka_utils.events import DataSet, BenchmarkEvent, FetcherStatus, DataSetSizeInfo
from bai_zk_utils.states import FetcherResult
from bai_zk_utils.zk_locker import RWLockManager, OnLockCallback, RWLock
from fetcher_dispatcher.data_set_manager import DataSetManager, DataSetDispatcher, DataSetOnDone, DataSetSizeEstimator

FILE_SIZE = 42

ZK_VERSION = 1

CLIENT_ID = "CLIENT_ID"

ACTION_ID = "ACTION_ID"

SOME_PATH = "/some/path"

SOME_SIZE_INFO = DataSetSizeInfo(FILE_SIZE, 1, FILE_SIZE)


def mock_size_estimator(src: str) -> DataSetSizeInfo:
    return SOME_SIZE_INFO


@fixture
def failing_size_estimator() -> DataSetSizeEstimator:
    mock = create_autospec(DataSetSizeEstimator)
    mock.side_effect = UnRetryableError()
    return mock


def data_set_to_path(client_id: str, action_id: str = None, dataset: DataSet = None) -> str:
    return SOME_PATH


def _mock_result_binary(status: FetcherStatus, msg: str = None):
    return FetcherResult(status, msg).to_binary()


BIN_RESULT_RUNNING = _mock_result_binary(FetcherStatus.RUNNING)
BIN_RESULT_PENDING = _mock_result_binary(FetcherStatus.PENDING)
BIN_RESULT_DONE = _mock_result_binary(FetcherStatus.DONE)
BIN_RESULT_CANCELED = _mock_result_binary(FetcherStatus.CANCELED)

ERROR_MESSAGE = "Error"


BIN_RESULT_FAILED = _mock_result_binary(FetcherStatus.FAILED, ERROR_MESSAGE)


def _mock_node_stat(version: int = ZK_VERSION):
    zk_node = create_autospec(ZnodeStat)
    zk_node.version = version
    return zk_node


def _mock_running_node():
    return mock.Mock(side_effect=[(BIN_RESULT_RUNNING, _mock_node_stat()), (BIN_RESULT_DONE, _mock_node_stat())])


def _mock_done_node():
    return mock.Mock(side_effect=[(BIN_RESULT_DONE, _mock_node_stat())])


def _mock_failed_node():
    return mock.Mock(side_effect=[(BIN_RESULT_FAILED, _mock_node_stat())])


def _mock_existing_node():
    return kazoo.exceptions.NodeExistsError()


@fixture
def zoo_keeper_client() -> KazooClient:
    return create_autospec(KazooClient)


@fixture
def zoo_keeper_client_with_done_node(zoo_keeper_client: KazooClient) -> KazooClient:
    zoo_keeper_client.get.side_effect = _mock_done_node()
    return zoo_keeper_client


@fixture
def zoo_keeper_client_with_running_node(zoo_keeper_client: KazooClient) -> KazooClient:
    zoo_keeper_client.get.side_effect = _mock_running_node()
    return zoo_keeper_client


@fixture
def zoo_keeper_client_with_node_that_exists(zoo_keeper_client: KazooClient) -> KazooClient:
    zoo_keeper_client.create.side_effect = _mock_existing_node()
    return zoo_keeper_client


@fixture
def zoo_keeper_client_with_running_node_that_exists(zoo_keeper_client_with_node_that_exists) -> KazooClient:
    zoo_keeper_client_with_node_that_exists.get.side_effect = _mock_running_node()
    return zoo_keeper_client_with_node_that_exists


@fixture
def zoo_keeper_client_with_done_node_that_exists(zoo_keeper_client_with_node_that_exists) -> KazooClient:
    zoo_keeper_client_with_node_that_exists.get.side_effect = _mock_done_node()
    return zoo_keeper_client_with_node_that_exists


@fixture
def kubernetes_job_starter() -> DataSetDispatcher:
    return create_autospec(DataSetDispatcher)


@fixture
def data_set_manager(
    zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher, mock_lock_manager: RWLockManager
) -> DataSetManager:
    data_set_manager = DataSetManager(
        zoo_keeper_client,
        kubernetes_job_starter,
        mock_lock_manager,
        data_set_to_path,
        size_estimator=mock_size_estimator,
    )
    return data_set_manager


@fixture
def some_data_set() -> DataSet:
    return DataSet("http://imagenet.org/bigdata.zip", size_info=SOME_SIZE_INFO)


@fixture
def enclosing_event() -> BenchmarkEvent:
    return BenchmarkEvent(
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


@fixture
def mock_lock() -> RWLock:
    return create_autospec(RWLock)


@fixture
def mock_lock_manager(mock_lock: RWLock) -> RWLockManager:
    def mock_instant_lock(state: Any, on_locked: OnLockCallback):
        on_locked(state, mock_lock)

    mock_locker = create_autospec(RWLockManager)
    mock_locker.acquire_write_lock.side_effect = mock_instant_lock
    return mock_locker


def test_pass_through_start(
    data_set_manager: DataSetManager,
    zoo_keeper_client: KazooClient,
    kubernetes_job_starter: DataSetDispatcher,
    mock_lock_manager: RWLockManager,
):
    data_set_manager.start()
    assert zoo_keeper_client.start.called


def test_pass_through_stop(
    data_set_manager: DataSetManager,
    zoo_keeper_client: KazooClient,
    kubernetes_job_starter: DataSetDispatcher,
    mock_lock_manager: RWLockManager,
):
    data_set_manager.stop()
    assert zoo_keeper_client.stop.called


def test_first_fast_success(
    zoo_keeper_client_with_done_node: KazooClient,
    some_data_set: DataSet,
    enclosing_event: BenchmarkEvent,
    kubernetes_job_starter: DataSetDispatcher,
    mock_lock_manager: RWLockManager,
    mock_lock: RWLock,
):
    on_done = _test_fetch(
        zoo_keeper_client_with_done_node, enclosing_event, kubernetes_job_starter, mock_lock_manager, some_data_set
    )

    _verify_fetch(enclosing_event, kubernetes_job_starter, some_data_set, mock_lock_manager)
    _verify_success(on_done, some_data_set, kubernetes_job_starter, zoo_keeper_client_with_done_node, mock_lock)


# Common part of the tests
def _test_fetch(zoo_keeper_client, enclosing_event, kubernetes_job_starter, mock_lock_manager, some_data_set):
    data_set_manager = DataSetManager(
        zoo_keeper_client,
        kubernetes_job_starter,
        mock_lock_manager,
        data_set_to_path,
        size_estimator=mock_size_estimator,
    )
    on_done = create_autospec(DataSetOnDone)
    data_set_manager.fetch(some_data_set, enclosing_event, on_done)
    return on_done


def test_first_wait_success(
    zoo_keeper_client_with_running_node: KazooClient,
    some_data_set: DataSet,
    enclosing_event: BenchmarkEvent,
    kubernetes_job_starter: DataSetDispatcher,
    mock_lock_manager: RWLockManager,
    mock_lock: RWLock,
):
    on_done = _test_fetch(
        zoo_keeper_client_with_running_node, enclosing_event, kubernetes_job_starter, mock_lock_manager, some_data_set
    )

    _verify_fetch(enclosing_event, kubernetes_job_starter, some_data_set, mock_lock_manager)
    _verify_wait_success(zoo_keeper_client_with_running_node)
    _verify_success(on_done, some_data_set, kubernetes_job_starter, zoo_keeper_client_with_running_node, mock_lock)


def _verify_fetch(
    enclosing_event: BenchmarkEvent,
    kubernetes_job_starter: DataSetDispatcher,
    some_data_set: DataSet,
    lock_manager: RWLockManager,
):
    kubernetes_job_starter.dispatch_fetch.assert_called_with(some_data_set, enclosing_event, SOME_PATH)
    lock_manager.acquire_write_lock.assert_called_once()


def _verify_wait_success(zoo_keeper_client: KazooClient):
    get_args, _ = zoo_keeper_client.get.call_args
    path, node_watcher = get_args
    assert path == SOME_PATH

    zk_node_evt = WatchedEvent(path=SOME_PATH, type=EventType.CHANGED, state=KeeperState.CONNECTED_RO)

    node_watcher(zk_node_evt)


def _verify_success(
    on_done: DataSetOnDone,
    data_set: DataSet,
    kubernetes_job_starter: DataSetDispatcher,
    zoo_keeper_client: KazooClient,
    lock: RWLock,
):
    assert data_set.status == FetcherStatus.DONE
    on_done.assert_called_with(data_set)
    zoo_keeper_client.delete.assert_called_with(SOME_PATH)
    kubernetes_job_starter.cleanup.assert_called_once()
    lock.release.assert_called_once()


DATASET_PATH = "dataset1"


@fixture
def zoo_keeper_client_to_cancel(zoo_keeper_client: KazooClient) -> KazooClient:
    zoo_keeper_client.get_children.return_value = [DATASET_PATH]
    zoo_keeper_client.get.return_value = (BIN_RESULT_RUNNING, _mock_node_stat())
    return zoo_keeper_client


@fixture
def zoo_keeper_client_with_conflict(zoo_keeper_client: KazooClient) -> KazooClient:
    zoo_keeper_client.get_children.return_value = [DATASET_PATH]
    zoo_keeper_client.get.side_effect = [
        (BIN_RESULT_RUNNING, _mock_node_stat(1)),
        (BIN_RESULT_RUNNING, _mock_node_stat(2)),
        (BIN_RESULT_DONE, _mock_node_stat(3)),
    ]
    zoo_keeper_client.set.side_effect = BadVersionError()
    return zoo_keeper_client


@fixture
def zoo_keeper_client_with_almost_done(zoo_keeper_client: KazooClient) -> KazooClient:
    zoo_keeper_client.get_children.return_value = [DATASET_PATH]
    # And then it's gone!
    zoo_keeper_client.get.side_effect = NoNodeError()
    return zoo_keeper_client


@fixture
def zoo_keeper_client_nothing_to_cancel(zoo_keeper_client: KazooClient) -> KazooClient:
    zoo_keeper_client.get_children.return_value = []
    return zoo_keeper_client


def test_cancel_happy_path(
    kubernetes_job_starter: DataSetDispatcher, zoo_keeper_client_to_cancel, mock_lock_manager: RWLockManager
):
    data_set_manager = DataSetManager(
        zoo_keeper_client_to_cancel, kubernetes_job_starter, mock_lock_manager, data_set_to_path
    )
    data_set_manager.cancel(CLIENT_ID, ACTION_ID)

    kubernetes_job_starter.cancel_all.assert_called_once_with(CLIENT_ID, ACTION_ID)
    zoo_keeper_client_to_cancel.set.assert_called_once_with(
        SOME_PATH + "/" + DATASET_PATH, BIN_RESULT_CANCELED, ZK_VERSION
    )


def test_cancel_node_is_done(
    kubernetes_job_starter: DataSetDispatcher,
    zoo_keeper_client_with_almost_done: KazooClient,
    mock_lock_manager: RWLockManager,
):
    data_set_manager = DataSetManager(
        zoo_keeper_client_with_almost_done, kubernetes_job_starter, mock_lock_manager, data_set_to_path
    )

    data_set_manager.cancel(CLIENT_ID, ACTION_ID)
    zoo_keeper_client_with_almost_done.set.assert_not_called()


def test_cancel_conflict(
    kubernetes_job_starter: DataSetDispatcher,
    zoo_keeper_client_with_conflict: KazooClient,
    mock_lock_manager: RWLockManager,
):
    data_set_manager = DataSetManager(
        zoo_keeper_client_with_conflict, kubernetes_job_starter, mock_lock_manager, data_set_to_path
    )

    data_set_manager.cancel(CLIENT_ID, ACTION_ID)
    # We expect 2 conflicts as stated in the fixture
    zoo_keeper_client_with_conflict.set.call_count == 2


def test_cancel_nothing_to_do(
    kubernetes_job_starter: DataSetDispatcher,
    zoo_keeper_client_nothing_to_cancel: KazooClient,
    mock_lock_manager: RWLockManager,
):
    data_set_manager = DataSetManager(
        zoo_keeper_client_nothing_to_cancel, kubernetes_job_starter, mock_lock_manager, data_set_to_path
    )
    data_set_manager.cancel(CLIENT_ID, ACTION_ID)

    zoo_keeper_client_nothing_to_cancel.set.assert_not_called()


def test_pass_through_estimator_error(
    enclosing_event: BenchmarkEvent,
    some_data_set: DataSet,
    failing_size_estimator: DataSetSizeEstimator,
    zoo_keeper_client: KazooClient,
    kubernetes_job_starter: DataSetDispatcher,
    mock_lock_manager: RWLockManager,
    mock_lock: RWLock,
):
    data_set_manager = DataSetManager(
        zoo_keeper_client, kubernetes_job_starter, mock_lock_manager, data_set_to_path, failing_size_estimator
    )
    on_done = create_autospec(DataSetOnDone)
    data_set_manager.fetch(some_data_set, enclosing_event, on_done)

    _verify_failed_estimator(mock_lock, on_done, some_data_set)


def _verify_failed_estimator(mock_lock, on_done, some_data_set):
    on_done.assert_called_once_with(some_data_set)
    assert some_data_set.status == FetcherStatus.FAILED
    mock_lock.release.assert_called_once()
