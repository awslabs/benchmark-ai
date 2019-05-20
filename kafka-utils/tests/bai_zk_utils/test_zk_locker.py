from kazoo.client import KazooClient
from unittest.mock import create_autospec, ANY

from pytest import fixture

from bai_zk_utils.zk_locker import DistributedRWLockManager, OnLockCallback

PREFIX = "/mylocks/"

NODE1 = "node1"
NODE2 = "node2"


def get_path(state: str):
    return f"state/{state}/"


def get_data(state: str):
    return b"42"


@fixture
def mock_zk_client() -> KazooClient:
    zk_client = create_autospec(KazooClient)

    children = []

    def mock_create(path, value=b"", ephemeral=False, sequence=False, makepath=False):
        myindex = len(children) + 1
        mypath = path + str(myindex)

        children.append(mypath)

        return mypath

    def mock_exists(path, watcher=None):
        return path in children

    def mock_get_children(path):
        return list(filter(lambda p: path in p, children))

    def mock_delete(path):
        children.remove(path)

    zk_client.create.side_effect = mock_create
    zk_client.exists.side_effect = mock_exists
    zk_client.get_children.side_effect = mock_get_children
    zk_client.delete.side_effect = mock_delete

    return zk_client


def test_the_first_one_read_lock(mock_zk_client: KazooClient):
    locker = DistributedRWLockManager(mock_zk_client, PREFIX, get_path)

    on_done = create_autospec(OnLockCallback)
    locker.acquire_read_lock(NODE1, on_done)

    on_done.assert_called_once_with(NODE1, ANY)


def test_the_read_locks_compat(mock_zk_client: KazooClient):
    locker = DistributedRWLockManager(mock_zk_client, PREFIX, get_path)

    on_done1 = create_autospec(OnLockCallback)
    on_done2 = create_autospec(OnLockCallback)

    locker.acquire_read_lock(NODE1, on_done1)
    locker.acquire_read_lock(NODE1, on_done2)

    on_done2.assert_called_once_with(NODE1, ANY)


def test_the_independent_writes(mock_zk_client: KazooClient):
    locker = DistributedRWLockManager(mock_zk_client, PREFIX, get_path)

    on_done1 = create_autospec(OnLockCallback)
    on_done2 = create_autospec(OnLockCallback)

    locker.acquire_write_lock(NODE1, on_done1)
    locker.acquire_write_lock(NODE2, on_done2)

    on_done1.assert_called_once_with(NODE1, ANY)
    on_done2.assert_called_once_with(NODE2, ANY)


def test_the_first_one_write_lock(mock_zk_client: KazooClient):
    locker = DistributedRWLockManager(mock_zk_client, PREFIX, get_path)

    on_done = create_autospec(OnLockCallback)
    locker.acquire_write_lock(NODE1, on_done)

    on_done.assert_called_once_with(NODE1, ANY)


def test_the_first_one_write_lock_after_read(mock_zk_client: KazooClient):
    locker = DistributedRWLockManager(mock_zk_client, PREFIX, get_path)

    on_done1 = create_autospec(OnLockCallback)
    on_done2 = create_autospec(OnLockCallback)

    locker.acquire_read_lock(NODE1, on_done1)
    locker.acquire_write_lock(NODE1, on_done2)

    on_done2.assert_not_called()


def test_the_first_read_after_write(mock_zk_client: KazooClient):
    locker = DistributedRWLockManager(mock_zk_client, PREFIX, get_path)

    on_done1 = create_autospec(OnLockCallback)
    on_done2 = create_autospec(OnLockCallback)

    locker.acquire_write_lock(NODE1, on_done1)
    locker.acquire_read_lock(NODE1, on_done2)

    on_done2.assert_not_called()
