from unittest import mock

import kazoo
import pytest
from kazoo.client import KazooClient

from bai_kafka_utils.events import DataSet
from benchmarkai_fetcher_job.states import FetcherResult, FetcherStatus
from fetcher_dispatcher.data_set_manager import DataSetManager, DataSetDispatcher, DataSetOnDone

DST = "s3://bucker/datasets.key"

SRC = "http://nowhere.com/very-bigdata.zip"

SOME_PATH = "/some/path"


def data_set_to_path(dataset: DataSet) -> str:
    return SOME_PATH


@pytest.fixture
def zoo_keeper_client() -> KazooClient:
    return mock.Mock()


def _mock_result_binary(status: FetcherStatus, msg: str = None):
    return FetcherResult(status, msg).to_binary()


BIN_RESULT_RUNNING = _mock_result_binary(FetcherStatus.RUNNING)
BIN_RESULT_PENDING = _mock_result_binary(FetcherStatus.PENDING)
BIN_RESULT_DONE = _mock_result_binary(FetcherStatus.DONE)


ERROR_MESSAGE = "Error"


BIN_RESULT_FAILED = _mock_result_binary(FetcherStatus.FAILED, ERROR_MESSAGE)


def _mock_running_node():
    return mock.Mock(side_effect=[[BIN_RESULT_RUNNING], [BIN_RESULT_DONE]])


def _mock_done_node():
    return mock.Mock(side_effect=[[BIN_RESULT_DONE]])


def _mock_failed_node():
    return mock.Mock(side_effect=[[BIN_RESULT_FAILED]])


def _mock_existing_node():
    return mock.Mock(side_effect=kazoo.exceptions.NodeExistsError())


def _zoo_keeper_client_with_node(_node_mock):
    zoo_keeper_client = mock.MagicMock()
    zoo_keeper_client.get = _node_mock
    return zoo_keeper_client


def _zoo_keeper_client_with_existing_node(_node_mock):
    zoo_keeper_client = _zoo_keeper_client_with_node(_node_mock)
    zoo_keeper_client.create = _mock_existing_node()
    return zoo_keeper_client


@pytest.fixture
def zoo_keeper_client_with_done_node() -> KazooClient:
    return _zoo_keeper_client_with_node(_mock_done_node())


@pytest.fixture
def zoo_keeper_client_with_failed_node() -> KazooClient:
    return _zoo_keeper_client_with_node(_mock_failed_node())


@pytest.fixture
def zoo_keeper_client_with_running_node() -> KazooClient:
    return _zoo_keeper_client_with_node(_mock_running_node())


@pytest.fixture
def zoo_keeper_client_with_running_node_that_exists() -> KazooClient:
    return _zoo_keeper_client_with_existing_node(_mock_running_node())


@pytest.fixture
def zoo_keeper_client_with_done_node_that_exists() -> KazooClient:
    return _zoo_keeper_client_with_existing_node(_mock_done_node())


@pytest.fixture
def kubernetes_job_starter() -> DataSetDispatcher:
    return mock.MagicMock()


@pytest.fixture
def data_set_manager(zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher) -> DataSetManager:
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter, data_set_to_path)
    return data_set_manager


@pytest.fixture
def some_data_set() -> DataSet:
    return DataSet(src=SRC, dst=DST)


def test_pass_through_start(zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher):
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter)
    data_set_manager.start()
    assert zoo_keeper_client.start.called


def test_pass_through_stop(zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher):
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter)
    data_set_manager.stop()
    assert zoo_keeper_client.stop.called


def test_first_fast_success(
    zoo_keeper_client_with_done_node: KazooClient, some_data_set: DataSet, kubernetes_job_starter: DataSetDispatcher
):
    data_set_manager = DataSetManager(zoo_keeper_client_with_done_node, kubernetes_job_starter, data_set_to_path)

    on_done = mock.MagicMock()

    data_set_manager.fetch(some_data_set, on_done)

    assert kubernetes_job_starter.called
    on_done.assert_called_with(DataSet(src=SRC, dst=DST, status=str(FetcherStatus.DONE)))


def test_first_fast_failed(
    zoo_keeper_client_with_failed_node: KazooClient, some_data_set: DataSet, kubernetes_job_starter: DataSetDispatcher
):
    data_set_manager = DataSetManager(zoo_keeper_client_with_failed_node, kubernetes_job_starter, data_set_to_path)

    on_done = mock.MagicMock()

    data_set_manager.fetch(some_data_set, on_done)

    assert kubernetes_job_starter.called
    on_done.assert_called_with(DataSet(src=SRC, status=str(FetcherStatus.FAILED), message=ERROR_MESSAGE))


def test_first_wait_success(
    zoo_keeper_client_with_running_node: KazooClient, some_data_set: DataSet, kubernetes_job_starter: DataSetDispatcher
):
    data_set_manager = DataSetManager(zoo_keeper_client_with_running_node, kubernetes_job_starter, data_set_to_path)

    on_done = mock.MagicMock()

    data_set_manager.fetch(some_data_set, on_done)

    assert kubernetes_job_starter.called
    assert not on_done.called

    _verify_wait_succes(on_done, zoo_keeper_client_with_running_node)


def test_second_already_done(
    zoo_keeper_client_with_done_node_that_exists: KazooClient,
    some_data_set: DataSet,
    kubernetes_job_starter: DataSetDispatcher,
):
    data_set_manager = DataSetManager(
        zoo_keeper_client_with_done_node_that_exists, kubernetes_job_starter, data_set_to_path
    )

    on_done = mock.MagicMock()

    data_set_manager.fetch(some_data_set, on_done)

    assert not kubernetes_job_starter.called
    assert on_done.called


def test_second_wait_success(
    zoo_keeper_client_with_running_node_that_exists: KazooClient,
    some_data_set: DataSet,
    kubernetes_job_starter: DataSetDispatcher,
):
    data_set_manager = DataSetManager(
        zoo_keeper_client_with_running_node_that_exists, kubernetes_job_starter, data_set_to_path
    )

    on_done = mock.MagicMock()

    data_set_manager.fetch(some_data_set, on_done)

    assert not kubernetes_job_starter.called
    assert not on_done.called

    _verify_wait_succes(on_done, zoo_keeper_client_with_running_node_that_exists)


def _verify_wait_succes(on_done: DataSetOnDone, zoo_keeper_client: KazooClient):
    get_args = zoo_keeper_client.get.call_args[0]
    assert get_args[0] == SOME_PATH

    zk_node_evt = mock.Mock()
    zk_node_evt.path = SOME_PATH

    node_watcher = get_args[1]
    node_watcher(zk_node_evt)

    assert on_done.called
