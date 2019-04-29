from kazoo.client import KazooClient
from typing import List, Callable

from bai_kafka_utils.events import BenchmarkEvent
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService
from fetcher_dispatcher.data_set_manager import DataSet, DataSetManager
from fetcher_dispatcher.data_set_pull import get_dataset_dst
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher


def create_data_set_manager(zookeeper_ensemble_hosts: str, kubeconfig: str, fetcher_job_image: str,
                            fetcher_node_selector: dict):
    zk_client = KazooClient(zookeeper_ensemble_hosts)
    job_dispatcher = KubernetesDispatcher(kubeconfig, fetcher_job_image, zookeeper_ensemble_hosts,
                                          fetcher_node_selector)

    return DataSetManager(zk_client, job_dispatcher)


class FetcherEventHandler(KafkaServiceCallback):
    def __init__(self, data_set_mgr: DataSetManager, s3_data_set_bucket: str):
        self.data_set_mgr = data_set_mgr
        self.s3_data_set_bucket = s3_data_set_bucket

    def handle_event(self, event: BenchmarkEvent, kafka_service: KafkaService):
        def extract_data_sets(event) -> List[DataSet]:
            return event.payload.data_sets

        def execute(task: DataSet, callback) -> None:
            task.dst = get_dataset_dst(task.uri, self.s3_data_set_bucket)

            self.data_set_mgr.fetch(task, callback)

        def execute_all(tasks: List[DataSet], callback: Callable) -> None:
            pending = list(tasks)

            def on_done(data_set: DataSet):
                pending.remove(data_set)
                if not pending:
                    callback()

            for tsk in tasks:
                execute(tsk, on_done)

        tasks = extract_data_sets(event)
        tasks = list(filter(lambda t: not t.dst, tasks))

        if not tasks:
            return

        def on_all_done():
            return event

        execute_all(tasks, on_all_done)

    def cleanup(self):
        self.data_set_mgr.stop()
