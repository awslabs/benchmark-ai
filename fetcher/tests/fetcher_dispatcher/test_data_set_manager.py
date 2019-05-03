from unittest import mock

import kazoo
import pytest
from kazoo.client import KazooClient

from bai_kafka_utils.events import DataSet
from fetcher_dispatcher.data_set_manager import (
    DataSetManager,
    DataSetDispatcher,
    DataSetOnDone,
)
from fetcher_dispatcher.fetch_state import FetchState

SOME_PATH = "/some/path"


def data_set_to_path(dataset: DataSet) -> str:
    return SOME_PATH


@pytest.fixture
def zoo_keeper_client() -> KazooClient:
    return mock.Mock()


def _mock_running_node():
    return mock.Mock(side_effect=[[FetchState.STATE_RUNNING], [FetchState.STATE_DONE]])


def _mock_done_node():
    return mock.Mock(side_effect=[[FetchState.STATE_DONE]])


def _mock_existing_node():
    return mock.Mock(side_effect=kazoo.exceptions.NodeExistsError())


@pytest.fixture
def zoo_keeper_client_with_done_node() -> KazooClient:
    zoo_keeper_client = mock.MagicMock()
    zoo_keeper_client.get = _mock_done_node()
    return zoo_keeper_client


@pytest.fixture
def zoo_keeper_client_with_running_node() -> KazooClient:
    zoo_keeper_client = mock.MagicMock()
    zoo_keeper_client.get = _mock_running_node()
    return zoo_keeper_client


@pytest.fixture
def zoo_keeper_client_with_running_node_that_exists() -> KazooClient:
    zoo_keeper_client = mock.MagicMock()
    zoo_keeper_client.get = _mock_running_node()
    zoo_keeper_client.create = _mock_existing_node()
    return zoo_keeper_client


@pytest.fixture
def zoo_keeper_client_with_done_node_that_exists() -> KazooClient:
    zoo_keeper_client = mock.MagicMock()
    zoo_keeper_client.get = _mock_done_node()
    zoo_keeper_client.create = _mock_existing_node()
    return zoo_keeper_client


@pytest.fixture
def kubernetes_job_starter() -> DataSetDispatcher:
    return mock.MagicMock()


@pytest.fixture
def data_set_manager(
    zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher
) -> DataSetManager:
    data_set_manager = DataSetManager(
        zoo_keeper_client, kubernetes_job_starter, data_set_to_path
    )
    return data_set_manager


@pytest.fixture
def some_data_set() -> DataSet:
    return DataSet("http://imagenet.org/bigdata.zip")


def test_pass_through_start(
    zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher
):
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter)
    data_set_manager.start()
    assert zoo_keeper_client.start.called


def test_pass_through_stop(
    zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher
):
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter)
    data_set_manager.stop()
    assert zoo_keeper_client.stop.called


def test_first_fast_success(
    zoo_keeper_client_with_done_node: KazooClient,
    some_data_set: DataSet,
    kubernetes_job_starter: DataSetDispatcher,
):
    data_set_manager = DataSetManager(
        zoo_keeper_client_with_done_node, kubernetes_job_starter, data_set_to_path
    )

    on_done = mock.MagicMock()

    data_set_manager.fetch(some_data_set, on_done)

    assert kubernetes_job_starter.called
    assert on_done.called


def test_first_wait_success(
    zoo_keeper_client_with_running_node: KazooClient,
    some_data_set: DataSet,
    kubernetes_job_starter: DataSetDispatcher,
):
    data_set_manager = DataSetManager(
        zoo_keeper_client_with_running_node, kubernetes_job_starter, data_set_to_path
    )

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
        zoo_keeper_client_with_done_node_that_exists,
        kubernetes_job_starter,
        data_set_to_path,
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
        zoo_keeper_client_with_running_node_that_exists,
        kubernetes_job_starter,
        data_set_to_path,
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
