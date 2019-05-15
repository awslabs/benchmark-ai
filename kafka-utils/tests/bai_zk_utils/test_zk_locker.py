from kazoo.client import KazooClient
from unittest.mock import create_autospec

from pytest import fixture

from bai_zk_utils.zk_locker import DistributedRWLocker, OnLockCallback

PREFIX = "/mylocks/"

NODE1 = "node1"
NODE2 = "node2"


def get_path(state: str):
    return f"state/{state}/"


@fixture
def mock_zk_client() -> KazooClient:
    zk_client = create_autospec(KazooClient)

    children = []

    def mock_create(path, ephemeral=False, sequence=False, makepath=False):
        myindex = len(children) + 1
        mypath = path + str(myindex)

        children.append(mypath)

        return mypath

    def mock_exists(path, watcher=None):
        return path in children

    zk_client.create.side_effect = mock_create
    zk_client.exists.side_effect = mock_exists
    zk_client.get_children.return_value = children

    return zk_client


def test_the_first_one_read_lock(mock_zk_client: KazooClient):
    locker = DistributedRWLocker(mock_zk_client, PREFIX, get_path)

    on_done = create_autospec(OnLockCallback)
    locker.acquire_read_lock(NODE1, on_done)

    on_done.assert_called_once()

def test_the_read_locks_compat(mock_zk_client: KazooClient):
    locker = DistributedRWLocker(mock_zk_client, PREFIX, get_path)

    on_done1 = create_autospec(OnLockCallback)
    on_done2 = create_autospec(OnLockCallback)
    
    locker.acquire_read_lock(NODE1, on_done1)
    locker.acquire_read_lock(NODE2, on_done2)

    on_done2.assert_called_once()


def test_the_first_one_write_lock(mock_zk_client: KazooClient):
    locker = DistributedRWLocker(mock_zk_client, PREFIX, get_path)

    on_done = create_autospec(OnLockCallback)
    locker.acquire_write_lock(NODE1, on_done)

    on_done.assert_called_once()

def test_the_first_one_write_lock_after_read(mock_zk_client: KazooClient):
    locker = DistributedRWLocker(mock_zk_client, PREFIX, get_path)

    on_done1 = create_autospec(OnLockCallback)
    on_done2 = create_autospec(OnLockCallback)

    locker.acquire_read_lock(NODE1, on_done1)
    locker.acquire_write_lock(NODE2, on_done2)

    on_done2.assert_not_called()

def test_the_first_one_write_lock_after_2(mock_zk_client: KazooClient):
    locker = DistributedRWLocker(mock_zk_client, PREFIX, get_path)

    on_done1 = create_autospec(OnLockCallback)
    on_done2 = create_autospec(OnLockCallback)

    locker.acquire_write_lock(NODE1, on_done1)
    locker.acquire_read_lock(NODE2, on_done2)

    on_done2.assert_not_called()
