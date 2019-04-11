# Zookeeper based fetch synchronizer
import os

from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError

from fetcher_dispatcher.events.data_set import DataSet
from fetcher_dispatcher.kubernetes_client import dispatch_fetcher
from fetcher_dispatcher.utils import md5sum

ZOOKEPER_ENSEBLE_HOSTS = os.environ.get("ZOOKEPER_ENSEBLE_HOSTS", "localhost:2181")

STATE_RUNNING = "RUNNING".encode("utf-8")
STATE_DONE = "DONE".encode("utf-8")
STATE_FAILED = "FAILED".encode("utf-8")


class DataSetManager:
    @staticmethod
    def __get_node_path(data_set: DataSet) -> str:
        return f"/data_sets/{md5sum(data_set.src)}"

    def __init__(self, zk: KazooClient = None, task_dispatcher: str = None, get_node_path: str = None):
        self._zk = zk or KazooClient(hosts=ZOOKEPER_ENSEBLE_HOSTS)
        self._task_dispatcher = task_dispatcher or dispatch_fetcher
        self._get_node_path = get_node_path or DataSetManager.__get_node_path

    def start(self) -> None:
        self._zk.start()

    def fetch(self, task: DataSet, on_done) -> None:

        zk_node_path = self._get_node_path(task)

        try:
            self._zk.create(zk_node_path, STATE_RUNNING, makepath=True)

            self._task_dispatcher(task)
        except NodeExistsError:
            pass

        self.__handle_node_state(zk_node_path, on_done)

    def __on_zk_changed(self, event, on_done):
        zk_node_path = event.path

        self.__handle_node_state(zk_node_path, on_done)

    def __handle_node_state(self, zk_node_path: str, on_done):
        def _on_zk_changed(evt):
            self.__on_zk_changed(evt, on_done)

        node_data = self._zk.get(zk_node_path, _on_zk_changed)
        if node_data[0] == STATE_DONE:
            on_done()

    def stop(self) -> None:
        self._zk.stop()
