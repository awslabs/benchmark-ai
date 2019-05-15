from unittest import mock

import kazoo
from kazoo.client import KazooClient
from pytest import fixture
from unittest.mock import create_autospec

from bai_kafka_utils.events import DataSet, BenchmarkEvent
from fetcher_dispatcher.data_set_manager import DataSetManager, DataSetDispatcher, DataSetOnDone
from fetcher_dispatcher.fetch_state import FetchState

SOME_PATH = "/some/path"


def data_set_to_path(dataset: DataSet) -> str:
    return SOME_PATH


@fixture
def zoo_keeper_client() -> KazooClient:
    return create_autospec(KazooClient)


def _mock_running_node():
    return [[FetchState.STATE_RUNNING], [FetchState.STATE_DONE]]


def _mock_done_node():
    return [[FetchState.STATE_DONE]]


def _mock_existing_node():
    return kazoo.exceptions.NodeExistsError()


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
def data_set_manager(zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher) -> DataSetManager:
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter, data_set_to_path)
    return data_set_manager


@fixture
def some_data_set() -> DataSet:
    return DataSet("http://imagenet.org/bigdata.zip")


@fixture
def enclosing_event() -> BenchmarkEvent:
    return BenchmarkEvent(
        action_id="DONTCARE",
        message_id="DONTCARE",
        client_id="DONTCARE",
        client_version="DONTCARE",
        client_username="DONTCARE",
        authenticated=False,
        tstamp=42,
        visited=[],
        payload="DONTCARE",
    )


def test_pass_through_start(zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher):
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter)
    data_set_manager.start()
    assert zoo_keeper_client.start.called


def test_pass_through_stop(zoo_keeper_client: KazooClient, kubernetes_job_starter: DataSetDispatcher):
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter)
    data_set_manager.stop()
    assert zoo_keeper_client.stop.called


def test_first_fast_success(
    zoo_keeper_client_with_done_node: KazooClient,
    some_data_set: DataSet,
    enclosing_event: BenchmarkEvent,
    kubernetes_job_starter: DataSetDispatcher,
):
    on_done = _test_fetch(zoo_keeper_client_with_done_node, enclosing_event, kubernetes_job_starter, some_data_set)

    kubernetes_job_starter.assert_called_with(some_data_set, enclosing_event, SOME_PATH)
    assert on_done.called


# Common part of the tests
def _test_fetch(zoo_keeper_client, enclosing_event, kubernetes_job_starter, some_data_set):
    data_set_manager = DataSetManager(zoo_keeper_client, kubernetes_job_starter, data_set_to_path)
    on_done = create_autospec(DataSetOnDone)
    data_set_manager.fetch(some_data_set, enclosing_event, on_done)
    return on_done


def test_first_wait_success(
    zoo_keeper_client_with_running_node: KazooClient,
    some_data_set: DataSet,
    enclosing_event: BenchmarkEvent,
    kubernetes_job_starter: DataSetDispatcher,
):
    on_done = _test_fetch(zoo_keeper_client_with_running_node, enclosing_event, kubernetes_job_starter, some_data_set)

    kubernetes_job_starter.assert_called_with(some_data_set, enclosing_event, SOME_PATH)
    assert not on_done.called

    _verify_wait_succes(on_done, zoo_keeper_client_with_running_node)


def test_second_already_done(
    zoo_keeper_client_with_done_node_that_exists: KazooClient,
    some_data_set: DataSet,
    enclosing_event: BenchmarkEvent,
    kubernetes_job_starter: DataSetDispatcher,
):
    on_done = _test_fetch(
        zoo_keeper_client_with_done_node_that_exists, enclosing_event, kubernetes_job_starter, some_data_set
    )

    assert not kubernetes_job_starter.called
    assert on_done.called


def test_second_wait_success(
    zoo_keeper_client_with_running_node_that_exists: KazooClient,
    some_data_set: DataSet,
    enclosing_event: BenchmarkEvent,
    kubernetes_job_starter: DataSetDispatcher,
):
    on_done = _test_fetch(
        zoo_keeper_client_with_running_node_that_exists, enclosing_event, kubernetes_job_starter, some_data_set
    )

    assert not kubernetes_job_starter.called
    assert not on_done.called

    _verify_wait_succes(on_done, zoo_keeper_client_with_running_node_that_exists)


def _verify_wait_succes(on_done: DataSetOnDone, zoo_keeper_client: KazooClient):
    get_args, _ = zoo_keeper_client.get.call_args
    assert get_args[0] == SOME_PATH

    zk_node_evt = mock.Mock()
    zk_node_evt.path = SOME_PATH

    node_watcher = get_args[1]
    node_watcher(zk_node_evt)

    assert on_done.called
