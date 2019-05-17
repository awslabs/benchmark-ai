import abc

from kazoo.client import KazooClient
from typing import Callable, Any


class RWLock(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def release(self):
        pass


OnLockCallback = Callable[[Any, RWLock], None]
PathCallback = Callable[[Any], str]
DataCallback = Callable[[Any], bytes]
IsCompatiblePredicate = Callable[[str, int], bool]


class RWLockManager(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def acquire_read_lock(self, state: Any, on_locked: OnLockCallback):
        pass

    @abc.abstractmethod
    def acquire_write_lock(self, state: Any, on_locked: OnLockCallback):
        pass


def _str_path(state):
    return str(state)


class DistributedLock(RWLock):
    def __init__(self, zk_client: KazooClient, node_path: str):
        self.zk_client = zk_client
        self.node_path = node_path

    def release(self):
        self.zk_client.delete(self.node_path)


class DistributedRWLockManager(RWLockManager):
    # We expect a started zk_client
    def __init__(self, zk_client: KazooClient, prefix: str, get_path: PathCallback = _str_path):
        self.zk_client = zk_client
        self.prefix = prefix
        self.get_path = get_path

    def get_lock_node_parent_path(self, state: Any):
        node_path = self.get_path(state)
        return f"/{self.prefix}/{node_path}"

    def _get_read_lock_path(self, state: Any):
        return f"{self.get_lock_node_parent_path(state)}/readlock-"

    def _get_write_lock_path(self, state: Any):
        return f"{self.get_lock_node_parent_path(state)}/writelock-"

    @staticmethod
    def get_sequence_index(path: str):
        last_delim = path.rindex("-")
        return int(path[last_delim + 1 :])

    @staticmethod
    def _incompatible_with_read(node_path: str, my_index: int):
        return "writelock-" in node_path and DistributedRWLockManager.get_sequence_index(node_path) < my_index

    @staticmethod
    def _incompatible_with_write(node_path: str, my_index: int):
        return DistributedRWLockManager.get_sequence_index(node_path) < my_index

    def _acquire_lock(
        self, state: Any, on_locked: OnLockCallback, get_path: PathCallback, is_incompat: IsCompatiblePredicate
    ):
        my_node_path_template = get_path(state)

        my_node_path = self.zk_client.create(my_node_path_template, ephemeral=True, sequence=True, makepath=True)

        self._acquire_lock_loop(state, on_locked, my_node_path, is_incompat)

    def _acquire_lock_loop(
        self, state: Any, on_locked: OnLockCallback, my_node_path: str, is_incompat: IsCompatiblePredicate
    ):
        my_index = DistributedRWLockManager.get_sequence_index(my_node_path)

        def _on_lock_changed():
            self._acquire_lock_loop(self, state, on_locked, my_node_path, is_incompat)
            pass

        while True:
            children = self.zk_client.get_children(self.get_lock_node_parent_path(state))
            relevant_children = list(filter(lambda path: is_incompat(path, my_index), children))

            if relevant_children:
                # We have to wait
                current_lock = relevant_children[0]
                locked = self.zk_client.exists(current_lock, _on_lock_changed)
                if locked:
                    # They call us later
                    return
            else:
                on_locked(state, DistributedLock(self.zk_client, my_node_path))
                return

    def acquire_read_lock(self, state: Any, on_locked: OnLockCallback):
        self._acquire_lock(state, on_locked, self._get_read_lock_path, DistributedRWLockManager._incompatible_with_read)

    def acquire_write_lock(self, state: Any, on_locked: OnLockCallback):
        self._acquire_lock(
            state, on_locked, self._get_write_lock_path, DistributedRWLockManager._incompatible_with_write
        )
