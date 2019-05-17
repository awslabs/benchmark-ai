# Zookeeper based fetch synchronizer
import logging

from kazoo.client import KazooClient
from kazoo.protocol.states import WatchedEvent, EventType
from typing import Callable

from bai_kafka_utils.events import DataSet, BenchmarkEvent
from bai_kafka_utils.utils import md5sum
from bai_zk_utils.states import FetcherResult, FetcherStatus
from bai_zk_utils.zk_locker import RWLockManager, RWLock

DataSetDispatcher = Callable[[DataSet, BenchmarkEvent, str], None]
NodePathSource = Callable[[DataSet], str]
DataSetOnDone = Callable[[DataSet], None]

logger = logging.getLogger(__name__)


def get_lock_name(data_set: DataSet) -> str:
    return md5sum(data_set.src)


class DataSetManager:
    @staticmethod
    def __get_node_path(data_set: DataSet) -> str:
        return f"/data_sets/{md5sum(data_set.src)}"

    INITIAL_DATA = FetcherResult(FetcherStatus.PENDING).to_binary()

    def __init__(
        self,
        zk: KazooClient,
        data_set_dispatcher: DataSetDispatcher,
        lock_manager: RWLockManager,
        get_node_path: NodePathSource = None,
    ):
        self._zk = zk
        self._data_set_dispatcher = data_set_dispatcher
        self._get_node_path = get_node_path or DataSetManager.__get_node_path

        self._lock_manager = lock_manager

    def start(self) -> None:
        logger.info("Start")
        self._zk.start()

    def fetch(self, data_set: DataSet, event: BenchmarkEvent, on_done: DataSetOnDone) -> None:
        logger.info("Fetch request %s", data_set)

        def on_data_set_locked(data_set: DataSet, lock: RWLock):
            def _on_done_and_unlock(data_set: DataSet):
                on_done(data_set)
                lock.release()

            # This node will be killed if I die
            zk_node_path = self._get_node_path(data_set)
            self._zk.create(zk_node_path, DataSetManager.INITIAL_DATA, ephemeral=True, makepath=True)

            self.__handle_node_state(zk_node_path, _on_done_and_unlock, data_set)

            self._data_set_dispatcher(data_set, event, zk_node_path)
            pass

        self._lock_manager.acquire_write_lock(data_set, on_data_set_locked)

    def __on_zk_changed(self, event: WatchedEvent, on_done: DataSetOnDone, data_set: DataSet):
        if event.type == EventType.DELETED:
            if not data_set.status:  # Something not final - and deleted???
                logger.error("Deleted node %s for the not finalized data_set %s", event.path, data_set)
                # TODO More sophisticated handling of that?
            return

        self.__handle_node_state(event.path, on_done, data_set)

    def __handle_node_state(self, zk_node_path: str, on_done: DataSetOnDone, data_set: DataSet):
        def _on_zk_changed(evt):
            self.__on_zk_changed(evt, on_done, data_set)

        node_data = self._zk.get(zk_node_path, _on_zk_changed)

        result: FetcherResult = FetcherResult.from_binary(node_data[0])

        logger.info("Fetch request %s result = %s", data_set, result)

        if result.status.final:
            data_set.status = str(result.status)

            if result.status == FetcherStatus.FAILED:
                data_set.message = result.message
                data_set.dst = None

            # We clean up
            self._zk.delete(zk_node_path)

            on_done(data_set)

    def stop(self) -> None:
        logger.info("Stop")
        self._zk.stop()
