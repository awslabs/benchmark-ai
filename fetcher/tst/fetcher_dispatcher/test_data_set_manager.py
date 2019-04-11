import kazoo
import mock
import pytest
from kazoo.client import KazooClient

from fetcher_dispatcher.data_set_manager import DataSetManager, DataSetDispatcher
from fetcher_dispatcher.events.data_set import DataSet
from fetcher_dispatcher.fetch_state import FetchState

SOME_PATH = "/some/path"


def data_set_to_path(dataset: DataSet) -> str:
    return SOME_PATH


@pytest.fixture
def zoo_keeper_client() -> KazooClient:
    return mock.Mock()


@pytest.fixture
def kubernetes_job_starter() -> DataSetDispatcher:
    return mock.MagicMock()


@pytest.fixture
def data_set_manager(zoo_keeper_client: KazooClient,
                     kubernetes_job_starter: DataSetDispatcher) -> DataSetManager:
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter, data_set_to_path)
    return data_set_manager


@pytest.fixture
def some_data_set() -> DataSet:
    return DataSet("http://imagenet.org/bigdata.zip")


def test_pass_through_start(data_set_manager: DataSetManager, zoo_keeper_client: KazooClient):
    data_set_manager.start()
    assert zoo_keeper_client.start.called


def test_pass_through_stop(data_set_manager: DataSetManager, zoo_keeper_client: KazooClient):
    data_set_manager.stop()
    assert zoo_keeper_client.stop.called


def test_first_fast_success(data_set_manager: DataSetManager, zoo_keeper_client: KazooClient, some_data_set: DataSet,
                            kubernetes_job_starter: DataSetDispatcher):
    on_done = mock.MagicMock()
    zoo_keeper_client.get = _mock_done_node()

    data_set_manager.fetch(some_data_set, on_done)

    assert kubernetes_job_starter.called
    assert on_done.called


def test_first_wait_success(data_set_manager: DataSetManager, zoo_keeper_client: KazooClient, some_data_set: DataSet,
                            kubernetes_job_starter: DataSetDispatcher):
    on_done = mock.MagicMock()
    zoo_keeper_client.get = _mock_wait_for_done()

    data_set_manager.fetch(some_data_set, on_done)

    assert kubernetes_job_starter.called
    assert not on_done.called

    _mock_wait_success(on_done, zoo_keeper_client)


def _mock_wait_for_done():
    return mock.Mock(side_effect=[[FetchState.STATE_RUNNING], [FetchState.STATE_DONE]])


def test_second_already_done(data_set_manager: DataSetManager, zoo_keeper_client: KazooClient, some_data_set: DataSet,
                             kubernetes_job_starter: DataSetDispatcher):
    on_done = mock.MagicMock()
    zoo_keeper_client.get = _mock_done_node()
    zoo_keeper_client.create = _mock_node_already_exists()

    data_set_manager.fetch(some_data_set, on_done)

    assert not kubernetes_job_starter.called
    assert on_done.called


def _mock_done_node():
    return mock.Mock(return_value=[FetchState.STATE_DONE])


def _mock_node_already_exists():
    return mock.Mock(side_effect=kazoo.exceptions.NodeExistsError())


def test_second_wait_success(data_set_manager: DataSetManager, zoo_keeper_client: KazooClient, some_data_set: DataSet,
                             kubernetes_job_starter: DataSetDispatcher):
    on_done = mock.MagicMock()
    zoo_keeper_client.get = _mock_wait_for_done()
    zoo_keeper_client.create = _mock_node_already_exists()

    data_set_manager.fetch(some_data_set, on_done)

    assert not kubernetes_job_starter.called
    assert not on_done.called

    _mock_wait_success(on_done, zoo_keeper_client)


def _mock_wait_success(on_done, zoo_keeper_client):
    args = zoo_keeper_client.get.call_args[0]
    assert args[0] == SOME_PATH
    evt = mock.Mock()
    evt.path = SOME_PATH
    args[1](evt)
    assert on_done.called
