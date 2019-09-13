# Zookeeper based fetch synchronizer
import abc
import logging
from typing import Callable, List, Optional, Tuple

from bai_kafka_utils.events import DataSet, BenchmarkEvent, FetcherStatus, DataSetSizeInfo
from bai_kafka_utils.utils import md5sum
from bai_zk_utils.states import FetcherResult
from bai_zk_utils.zk_locker import RWLockManager, RWLock
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError, BadVersionError
from kazoo.protocol.states import WatchedEvent, EventType

from preflight.estimator import estimate_fetch_size

DataSetDispatcher = Callable[[DataSet, BenchmarkEvent, str], None]


class DataSetDispatcher(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def dispatch_fetch(self, task: DataSet, event: BenchmarkEvent, zk_node_path: str):
        pass

    @abc.abstractmethod
    def cancel_all(self, client_id: str, action_id: str = None):
        pass

    @abc.abstractmethod
    def cleanup(self, task: DataSet, event: BenchmarkEvent):
        pass


# client_id/action_id/dataset
NodePathSource = Callable[[str, Optional[str], Optional[DataSet]], str]


DataSetOnDone = Callable[[DataSet], None]

DataSetSizeEstimator = Callable[[str], DataSetSizeInfo]

logger = logging.getLogger(__name__)


def get_lock_name(data_set: DataSet) -> str:
    return md5sum(data_set.src)


class DataSetManager:
    @staticmethod
    def __get_node_path(client_id: str, action_id: str = None, data_set: DataSet = None) -> str:
        # MD5 has impact on the node - so different locks etc.
        path = f"/data_sets/{client_id}"
        if action_id:
            path += f"/{action_id}"
            if data_set:
                path += f"/{md5sum(str(data_set))}"
        return path

    INITIAL_DATA = FetcherResult(FetcherStatus.PENDING).to_binary()

    @staticmethod
    def _set_failed(data_set: DataSet, message: str):
        data_set.message = message
        data_set.status = FetcherStatus.FAILED
        data_set.dst = None

    def __init__(
        self,
        zk: KazooClient,
        data_set_dispatcher: DataSetDispatcher,
        lock_manager: RWLockManager,
        get_node_path: NodePathSource = None,
        size_estimator: DataSetSizeEstimator = None,
    ):
        self._zk = zk
        self._data_set_dispatcher = data_set_dispatcher
        self._get_node_path = get_node_path or DataSetManager.__get_node_path

        self._lock_manager = lock_manager
        self._size_estimator = size_estimator or estimate_fetch_size

    def start(self) -> None:
        logger.info("Start")
        self._zk.start()

    def fetch(self, data_set: DataSet, event: BenchmarkEvent, on_done: DataSetOnDone) -> None:
        logger.info("Fetch request %s", data_set)

        def on_data_set_locked(data_set: DataSet, lock: RWLock):
            def _on_done_and_unlock(data_set: DataSet):
                on_done(data_set)
                self._data_set_dispatcher.cleanup(data_set, event)
                lock.release()

            try:
                data_set.size_info = self._size_estimator(data_set.src)
            except Exception as e:
                msg = f"Failed to estimate the size of dataset {data_set.src}: {str(e)}"
                logger.exception(f"{msg}")
                FetcherResult(FetcherStatus.FAILED, None, msg).update(data_set)
                on_done(data_set)
                lock.release()
                return

            # This node will be killed if I die
            zk_node_path = self._get_node_path(event.client_id, event.action_id, data_set)
            self._zk.create(zk_node_path, DataSetManager.INITIAL_DATA, ephemeral=True, makepath=True)

            self.__handle_node_state(zk_node_path, _on_done_and_unlock, data_set)

            data_set.size_info = self._size_estimator(data_set.src)

            self._data_set_dispatcher.dispatch_fetch(data_set, event, zk_node_path)

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

        data, _ = self._zk.get(zk_node_path, _on_zk_changed)

        result: FetcherResult = FetcherResult.from_binary(data)

        logger.info("Fetch request %s result = %s", data_set, result)

        if result.status.final:
            result.update(data_set)

            # We clean up
            self._zk.delete(zk_node_path)

            on_done(data_set)

    def stop(self) -> None:
        logger.info("Stop")
        self._zk.stop()

    def cancel(self, client_id: str, action_id: str) -> Tuple[List[str], int]:
        logger.info(f"Canceling action {client_id}/{action_id}")
        return (
            self._data_set_dispatcher.cancel_all(client_id, action_id),
            self._update_nodes_to_cancel(client_id, action_id),
        )

    def _update_nodes_to_cancel(self, client_id: str, action_id: str) -> int:
        # As always with stop-flags, we can face a bunch of race conditions
        zk_node_path = self._get_node_path(client_id, action_id)

        number_of_nodes_updated = 0

        try:
            for child in self._zk.get_children(zk_node_path):
                abs_path = zk_node_path + "/" + child

                logger.info(f"Updating node {abs_path}")

                try:
                    while True:
                        data, zk_stat = self._zk.get(abs_path)

                        result: FetcherResult = FetcherResult.from_binary(data)

                        # The guy is final - it will not take long for us to cancel it.
                        # The job is finished.
                        # So now we are in a race with a zookeeper listener, that will pass the results downstream.
                        if result.status.final:
                            logger.info(f"{abs_path}: not to be canceled - already finished")
                            break
                        result.status = FetcherStatus.CANCELED

                        new_data = result.to_binary()
                        try:
                            self._zk.set(abs_path, new_data, version=zk_stat.version)
                            number_of_nodes_updated = number_of_nodes_updated + 1
                        except BadVersionError:
                            logger.info(f"{abs_path}: the node was updated meanwhile")
                            continue
                        logger.info(f"{abs_path}: canceled")
                        break

                except NoNodeError:
                    logger.info(f"{abs_path}: the node was deleted meanwhile")
                    # The task was just finished - status was repopted to customer and the node got deleted.
                    # OK. It's not our deal anymore
                    continue
        except NoNodeError:
            # Absorb NoNodeError
            logger.info(f"{zk_node_path}: node not found")

        return number_of_nodes_updated
