# Zookeeper based fetch synchronizer
import logging

from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError
from typing import Callable

from bai_kafka_utils.events import DataSet
from fetcher_dispatcher.fetch_state import FetchState
from bai_kafka_utils.utils import md5sum


DataSetDispatcher = Callable[[DataSet, str], None]
NodePathSource = Callable[[DataSet], str]
DataSetOnDone = Callable[[DataSet], None]

logger = logging.getLogger(__name__)


class DataSetManager:
    @staticmethod
    def __get_node_path(data_set: DataSet) -> str:
        return f"/data_sets/{md5sum(data_set.src)}"

    def __init__(self, zk: KazooClient, data_set_dispatcher: DataSetDispatcher, get_node_path: NodePathSource = None):
        self._zk = zk
        self._data_set_dispatcher = data_set_dispatcher
        self._get_node_path = get_node_path or DataSetManager.__get_node_path

    def start(self) -> None:
        logger.info("Start")
        self._zk.start()

    def fetch(self, data_set: DataSet, on_done) -> None:
        logger.info("Fetch request %s", data_set)

        zk_node_path = self._get_node_path(data_set)
        logger.info("zk_node_path=%s", zk_node_path)

        try:
            self._zk.create(zk_node_path, FetchState.STATE_RUNNING, makepath=True)

            logger.info("Node lock %s acquired", zk_node_path)

            self._data_set_dispatcher(data_set, zk_node_path)
        except NodeExistsError:
            logger.info("Node %s already exists", zk_node_path)

        self.__handle_node_state(zk_node_path, on_done, data_set)

    def __on_zk_changed(self, event, on_done: DataSetOnDone, data_set: DataSet):
        zk_node_path = event.path

        self.__handle_node_state(zk_node_path, on_done, data_set)

    def __handle_node_state(self, zk_node_path: str, on_done: DataSetOnDone, data_set: DataSet):
        def _on_zk_changed(evt):
            self.__on_zk_changed(evt, on_done, data_set)

        node_data = self._zk.get(zk_node_path, _on_zk_changed)
        if node_data[0] == FetchState.STATE_DONE:
            on_done(data_set)

    def stop(self) -> None:
        logger.info("Stop")
        self._zk.stop()
