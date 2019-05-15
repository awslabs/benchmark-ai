from kazoo.client import KazooClient
from typing import Callable, Any


class DistributedLock:
    def release(self):
        pass


OnLockCallback = Callable[[Any, DistributedLock], None]
PathCallback = Callable[[Any], str]
IsCompatiblePredicate = Callable[[str, int], bool]


class DistributedRWLocker:
    def __init__(self, zk_client: KazooClient, prefix: str, get_path: PathCallback):
        self.zk_client = zk_client
        self.prefix = prefix
        self.get_path = get_path

    def get_lock_node_parent_path(self, state: Any):
        node_path = self.get_path(state)
        return f"{self.prefix}/{node_path}"

    def _get_read_lock_path(self, state: Any):
        return f"{self.get_lock_node_parent_path(state)}/readlock-"

    def _get_write_lock_path(self, state: Any):
        return f"{self.get_lock_node_parent_path(state)}/writelock-"

    @classmethod
    def get_sequence_index(cls, path: str):
        last_delim = path.rindex("-")
        return int(path[last_delim + 1 :])

    @classmethod
    def _incompatible_with_read(cls, node_path: str, my_index: int):
        return "writelock-" in node_path and DistributedRWLocker.get_sequence_index(node_path) < my_index

    @classmethod
    def _incompatible_with_write(cls, node_path: str, my_index: int):
        return DistributedRWLocker.get_sequence_index(node_path) < my_index

    def _acquire_lock(
        self, state: Any, on_locked: OnLockCallback, get_path: PathCallback, is_incompat: IsCompatiblePredicate
    ):
        my_node_path_template = get_path(state)
        my_node_path = self.zk_client.create(my_node_path_template, ephemeral=True, sequence=True, makepath=True)

        my_index = DistributedRWLocker.get_sequence_index(my_node_path)

        self._acquire_lock_loop(state, on_locked, my_index, is_incompat)

    def _acquire_lock_loop(
        self, state: Any, on_locked: OnLockCallback, my_index: int, is_incompat: IsCompatiblePredicate
    ):
        def _on_lock_changed():
            self._acquire_lock_loop(self, state, on_locked, my_index, is_incompat)
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
                on_locked(state, DistributedLock())
                return

    def acquire_read_lock(self, state: Any, on_locked: OnLockCallback):
        self._acquire_lock(state, on_locked, self._get_read_lock_path, DistributedRWLocker._incompatible_with_read)

    def acquire_write_lock(self, state: Any, on_locked: OnLockCallback):
        self._acquire_lock(state, on_locked, self._get_write_lock_path, DistributedRWLocker._incompatible_with_write)
