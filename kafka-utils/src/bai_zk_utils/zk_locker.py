import abc
import logging

from kazoo.client import KazooClient
from kazoo.protocol.states import WatchedEvent
from typing import Callable, Any

from bai_kafka_utils.utils import md5sum

READLOCK_SUFFIX = "readlock-"

WRITELOCK_SUFFIX = "writelock-"

logger = logging.getLogger(__name__)


class RWLock(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def release(self):
        pass


OnLockCallback = Callable[[Any, RWLock], None]
PathCallback = Callable[[Any], str]
DataCallback = Callable[[Any], bytes]
IsIncompatiblePredicate = Callable[[str], bool]


class RWLockManager(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def acquire_read_lock(self, state: Any, on_locked: OnLockCallback):
        pass

    @abc.abstractmethod
    def acquire_write_lock(self, state: Any, on_locked: OnLockCallback):
        pass


def _str_path(state):
    return md5sum(str(state))


class DistributedLock(RWLock):
    def __init__(self, zk_client: KazooClient, node_path: str):
        self.zk_client = zk_client
        self.node_path = node_path

    def release(self):
        logger.info(f"Unlock delete {self.node_path}")
        self.zk_client.delete(self.node_path)


# Implements ZooKeepers cookebook distributed locks.
# See here https://zookeeper.apache.org/doc/r3.1.2/recipes.html#Shared+Locks
class DistributedRWLockManager(RWLockManager):
    # We expect a started zk_client
    def __init__(self, zk_client: KazooClient, prefix: str, get_path: PathCallback = _str_path):
        self.zk_client = zk_client
        self.prefix = prefix
        self.get_path = get_path

    def get_lock_node_parent_path(self, state: Any):
        node_path = self.get_path(state)
        return DistributedRWLockManager._get_abs_path(self.prefix, node_path)

    def _get_read_lock_path(self, state: Any):
        return DistributedRWLockManager._get_abs_path(self.get_lock_node_parent_path(state), READLOCK_SUFFIX)

    def _get_write_lock_path(self, state: Any):
        return DistributedRWLockManager._get_abs_path(self.get_lock_node_parent_path(state), WRITELOCK_SUFFIX)

    @staticmethod
    def _get_abs_path(parent, child):
        return f"{parent}/{child}"

    @staticmethod
    def get_sequence_index(path: str):
        last_delim = path.rindex("-")
        return int(path[last_delim + 1 :])

    @staticmethod
    def _incompatible_with_read(node_path: str):
        return WRITELOCK_SUFFIX in node_path

    @staticmethod
    def _incompatible_with_write(node_path: str):
        return True

    def _acquire_lock(
        self, state: Any, on_locked: OnLockCallback, get_path: PathCallback, is_incompat: IsIncompatiblePredicate
    ):
        my_node_path_template = get_path(state)
        # Don't use state in the loop to avoid issues with mutable objects.
        # State is passed only to be passed to on_locked
        state_path = self.get_lock_node_parent_path(state)

        my_node_path = self.zk_client.create(my_node_path_template, ephemeral=True, sequence=True, makepath=True)

        self._acquire_lock_loop(state, state_path, on_locked, my_node_path, is_incompat)

    def _acquire_lock_loop(
        self,
        state: Any,
        state_path: str,
        on_locked: OnLockCallback,
        my_node_path: str,
        is_incompat: IsIncompatiblePredicate,
    ):
        my_index = DistributedRWLockManager.get_sequence_index(my_node_path)

        def _on_lock_changed(event: WatchedEvent):
            logger.info(f"Trace _on_changed with {my_node_path}")
            self._acquire_lock_loop(state, state_path, on_locked, my_node_path, is_incompat)
            pass

        # This is not an infinite loop.
        # It does just one step if:
        # - we lock it immediately
        # - we should wait
        # It continues ONLY if the current locking node was deleted between get_children and exists
        # Since this makes us one position closer to our goal - this cannot happen infinitely
        logger.info(f"Enter lock loop on {state_path} with {my_index}")

        while True:
            logger.info(f"Calling get children for {state_path}")
            children = self.zk_client.get_children(state_path)

            # Nodes before me to lock the resource
            locks_before = list(
                path
                for path in children
                if DistributedRWLockManager.get_sequence_index(path) < my_index and is_incompat(path)
            )

            if locks_before:
                # We have to wait
                rel_current_lock = locks_before[0]
                current_lock = DistributedRWLockManager._get_abs_path(state_path, rel_current_lock)
                locked = self.zk_client.exists(current_lock, _on_lock_changed)
                if locked:
                    # They call us later
                    return
                # Since it's a rare case, let's do some logging
                logger.info(f"Lock is awaited by {locks_before}")
                logger.info(f"{current_lock} seems to be removed by other process just now")
                logger.info(f"Continue lock loop {state_path}")
            else:
                on_locked(state, DistributedLock(self.zk_client, my_node_path))
                return

    def acquire_read_lock(self, state: Any, on_locked: OnLockCallback):
        self._acquire_lock(state, on_locked, self._get_read_lock_path, DistributedRWLockManager._incompatible_with_read)

    def acquire_write_lock(self, state: Any, on_locked: OnLockCallback):
        self._acquire_lock(
            state, on_locked, self._get_write_lock_path, DistributedRWLockManager._incompatible_with_write
        )
