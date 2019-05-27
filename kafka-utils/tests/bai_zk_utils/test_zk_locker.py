from kazoo.exceptions import NoNodeError
from kazoo.protocol.states import WatchedEvent, EventType, KazooState
from typing import List, Dict, Callable

from kazoo.client import KazooClient
from unittest.mock import create_autospec, ANY

from pytest import fixture

from bai_zk_utils.zk_locker import DistributedRWLockManager, OnLockCallback, DistributedLock, RWLock

PREFIX = "/mylocks/"

NODE1 = "node1"
NODE2 = "node2"


def get_path(state: str):
    return f"state/{state}/"


def get_data(state: str):
    return b"42"


KazooWatcher = Callable[[WatchedEvent], None]

NOT_SUPPORTED_YET = "Can not simulate this yet"

# While we generally highly convinced, that mocks should be simple and it's not a good idea to simulate
# the complex behaviour with it, we think it makes sense to implement this easy KazooClient simulator
@fixture
def mock_zk_client() -> KazooClient:
    zk_client = create_autospec(KazooClient)

    nodes: Dict[str, List[KazooWatcher]] = {}

    def mock_create(path, value=b"", ephemeral=False, sequence=False, makepath=False):

        if sequence:
            myindex = len(nodes) + 1
            path = path + str(myindex)

        nodes[path] = []

        return path

    def mock_exists(path, watcher: KazooWatcher = None):
        exists = any(True for p in nodes.keys() if p.startswith(path))
        if watcher:
            if exists:
                nodes[path].append(watcher)
            else:
                assert False, NOT_SUPPORTED_YET
        return exists

    # No support for watchers yet
    def mock_get_children(path: str):
        if not mock_exists(path):
            raise NoNodeError(f"{path} not found")
        return [p.replace(path + "/", "") for p in nodes.keys() if p.startswith(path) and p != path]

    # No recursive yet
    def mock_delete(path: str):
        if not mock_exists(path):
            raise NoNodeError(f"{path} not found")

        # Recursive delete in any form
        for node_path, watchers in nodes.items():
            if node_path.startswith(path) and path != node_path:
                assert False, NOT_SUPPORTED_YET

        watchers = nodes.pop(path)
        for watcher in watchers:
            event = WatchedEvent(EventType.DELETED, path, KazooState.CONNECTED)
            watcher(event)

    zk_client.create.side_effect = mock_create
    zk_client.exists.side_effect = mock_exists
    zk_client.get_children.side_effect = mock_get_children
    zk_client.delete.side_effect = mock_delete

    return zk_client


@fixture
def locker(mock_zk_client: KazooClient) -> DistributedRWLockManager:
    return DistributedRWLockManager(mock_zk_client, PREFIX, get_path)


@fixture
def on_done1(mocker):
    return mocker.create_autospec(OnLockCallback)


@fixture
def on_done2(mocker):
    return mocker.create_autospec(OnLockCallback)


def get_lock(on_lock: OnLockCallback) -> RWLock:
    args, _ = on_lock.call_args
    assert isinstance(args[1], DistributedLock)
    return args[1]


def test_the_first_one_read_lock(locker: DistributedRWLockManager, on_done1: OnLockCallback):
    locker.acquire_read_lock(NODE1, on_done1)

    on_done1.assert_called_once_with(NODE1, ANY)


def test_the_read_locks_compat(locker: DistributedRWLockManager, on_done1: OnLockCallback, on_done2: OnLockCallback):
    locker.acquire_read_lock(NODE1, on_done1)
    locker.acquire_read_lock(NODE1, on_done2)

    on_done2.assert_called_once_with(NODE1, ANY)


def test_the_independent_writes(locker: DistributedRWLockManager, on_done1: OnLockCallback, on_done2: OnLockCallback):

    locker.acquire_write_lock(NODE1, on_done1)
    locker.acquire_write_lock(NODE2, on_done2)

    on_done1.assert_called_once_with(NODE1, ANY)
    on_done2.assert_called_once_with(NODE2, ANY)


def test_the_first_one_write_lock(locker: DistributedRWLockManager, on_done1: OnLockCallback):
    locker.acquire_write_lock(NODE1, on_done1)

    on_done1.assert_called_once_with(NODE1, ANY)


def test_the_first_one_write_lock_after_read(
    locker: DistributedRWLockManager, on_done1: OnLockCallback, on_done2: OnLockCallback
):

    locker.acquire_read_lock(NODE1, on_done1)
    locker.acquire_write_lock(NODE1, on_done2)

    on_done2.assert_not_called()


# Wrong impl once can cause infinite loop
def test_the_first_read_after_write(
    locker: DistributedRWLockManager, on_done1: OnLockCallback, on_done2: OnLockCallback
):
    locker.acquire_write_lock(NODE1, on_done1)
    locker.acquire_read_lock(NODE1, on_done2)

    on_done2.assert_not_called()


# Wrong impl once can cause infinite loop
def test_the_first_write_after_write(
    locker: DistributedRWLockManager, on_done1: OnLockCallback, on_done2: OnLockCallback
):
    locker.acquire_write_lock(NODE1, on_done1)
    locker.acquire_write_lock(NODE1, on_done2)

    on_done2.assert_not_called()

    lock1 = get_lock(on_done1)
    lock1.release()

    on_done2.assert_called_once_with(NODE1, ANY)


def test_mutable_has_no_effect(locker: DistributedRWLockManager, on_done1: OnLockCallback, on_done2: OnLockCallback):
    state = {"foo": "bar"}

    locker.acquire_write_lock(state, on_done1)
    locker.acquire_write_lock(state, on_done2)

    state["foo"] = "not bar"

    lock1 = get_lock(on_done1)
    lock1.release()
    on_done2.assert_called_once_with(state, ANY)
