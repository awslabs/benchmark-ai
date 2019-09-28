# Zookeeper based fetch synchronizer
import abc
import logging
from typing import Callable, List, Optional, Tuple

from bai_kafka_utils.events import DownloadableContent, BenchmarkEvent, FetcherStatus, ContentSizeInfo
from bai_kafka_utils.utils import md5sum
from bai_zk_utils.states import FetcherResult
from bai_zk_utils.zk_locker import RWLockManager, RWLock
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError, BadVersionError
from kazoo.protocol.states import WatchedEvent, EventType

from preflight.estimator import estimate_fetch_size


class DownloadDispatcher(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def dispatch_fetch(self, task: DownloadableContent, event: BenchmarkEvent, zk_node_path: str):
        pass

    @abc.abstractmethod
    def cancel_all(self, client_id: str, action_id: str = None):
        pass

    @abc.abstractmethod
    def cleanup(self, task: DownloadableContent, event: BenchmarkEvent):
        pass


# client_id/action_id/dowloadable_content
NodePathSource = Callable[[str, Optional[str], Optional[DownloadableContent]], str]


DownloadOnDone = Callable[[DownloadableContent], None]

ContentSizeEstimator = Callable[[str], ContentSizeInfo]

logger = logging.getLogger(__name__)


def get_lock_name(content: DownloadableContent) -> str:
    return md5sum(content.src)


class DownloadManager:
    @staticmethod
    def __get_node_path(client_id: str, action_id: str = None, content: DownloadableContent = None) -> str:
        # MD5 has impact on the node - so different locks etc.
        path = f"/downloads/{client_id}"
        if action_id:
            path += f"/{action_id}"
            if content:
                path += f"/{md5sum(str(content))}"
        return path

    INITIAL_DATA = FetcherResult(FetcherStatus.PENDING).to_binary()

    @staticmethod
    def _set_failed(content: DownloadableContent, message: str):
        content.message = message
        content.status = FetcherStatus.FAILED
        content.dst = None

    def __init__(
        self,
        zk: KazooClient,
        download_dispatcher: DownloadDispatcher,
        lock_manager: RWLockManager,
        get_node_path: NodePathSource = None,
        size_estimator: ContentSizeEstimator = None,
    ):
        self._zk = zk
        self._download_dispatcher = download_dispatcher
        self._get_node_path = get_node_path or DownloadManager.__get_node_path

        self._lock_manager = lock_manager
        self._size_estimator = size_estimator or estimate_fetch_size

    def start(self) -> None:
        logger.info("Start")
        self._zk.start()

    def fetch(self, content: DownloadableContent, event: BenchmarkEvent, on_done: DownloadOnDone) -> None:
        logger.info("Fetch request %s", content)

        def on_content_locked(content: DownloadableContent, lock: RWLock):
            def _on_done_and_unlock(content: DownloadableContent):
                on_done(content)
                self._download_dispatcher.cleanup(content, event)
                lock.release()

            try:
                content.size_info = self._size_estimator(content.src)
            except Exception as e:
                msg = f"Failed to estimate the size of content {content.src}: {str(e)}"
                logger.exception(f"{msg}")
                FetcherResult(FetcherStatus.FAILED, None, msg).update(content)
                on_done(content)
                lock.release()
                return

            # This node will be killed if I die
            zk_node_path = self._get_node_path(event.client_id, event.action_id, content)
            self._zk.create(zk_node_path, DownloadManager.INITIAL_DATA, ephemeral=True, makepath=True)

            self.__handle_node_state(zk_node_path, _on_done_and_unlock, content)

            content.size_info = self._size_estimator(content.src)

            self._download_dispatcher.dispatch_fetch(content, event, zk_node_path)

        self._lock_manager.acquire_write_lock(content, on_content_locked)

    def __on_zk_changed(self, event: WatchedEvent, on_done: DownloadOnDone, content: DownloadableContent):
        if event.type == EventType.DELETED:
            if not content.status:  # Something not final - and deleted???
                logger.error("Deleted node %s for the not finalized content %s", event.path, content)
                # TODO More sophisticated handling of that?
            return

        self.__handle_node_state(event.path, on_done, content)

    def __handle_node_state(self, zk_node_path: str, on_done: DownloadOnDone, content: DownloadableContent):
        def _on_zk_changed(evt):
            self.__on_zk_changed(evt, on_done, content)

        data, _ = self._zk.get(zk_node_path, _on_zk_changed)

        result: FetcherResult = FetcherResult.from_binary(data)

        logger.info("Fetch request %s result = %s", content, result)

        if result.status.final:
            result.update(content)

            # We clean up
            self._zk.delete(zk_node_path)

            on_done(content)

    def stop(self) -> None:
        logger.info("Stop")
        self._zk.stop()

    def cancel(self, client_id: str, action_id: str) -> Tuple[List[str], int]:
        logger.info(f"Canceling action {client_id}/{action_id}")
        return (
            self._download_dispatcher.cancel_all(client_id, action_id),
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
