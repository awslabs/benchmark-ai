from kazoo.client import KazooClient
from typing import List, Callable

from bai_kafka_utils.cmd_callback import KafkaCommandCallback
from bai_kafka_utils.events import FetcherBenchmarkEvent, Status, FetcherStatus
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name
from bai_zk_utils.zk_locker import DistributedRWLockManager
from fetcher_dispatcher import SERVICE_NAME, __version__
from fetcher_dispatcher.args import FetcherServiceConfig, FetcherJobConfig
from fetcher_dispatcher.data_set_manager import DataSet, DataSetManager, get_lock_name
from fetcher_dispatcher.data_set_pull import get_dataset_dst
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher

LOCK_MANAGER_PREFIX = "fetcher_lock_manager"


def create_data_set_manager(zookeeper_ensemble_hosts: str, kubeconfig: str, fetcher_job: FetcherJobConfig):
    zk_client = KazooClient(zookeeper_ensemble_hosts)
    job_dispatcher = KubernetesDispatcher(kubeconfig, zookeeper_ensemble_hosts, fetcher_job)

    lock_manager = DistributedRWLockManager(zk_client, LOCK_MANAGER_PREFIX, get_lock_name)

    return DataSetManager(zk_client, job_dispatcher, lock_manager)


class FetcherEventHandler(KafkaServiceCallback):
    def __init__(self, producer_topic: str, data_set_mgr: DataSetManager, s3_data_set_bucket: str):
        self.data_set_mgr = data_set_mgr
        self.s3_data_set_bucket = s3_data_set_bucket
        self.producer_topic = producer_topic

    @staticmethod
    def _collect_status(data_sets: List[DataSet]) -> Status:
        for fetch_status in [d.status for d in data_sets]:
            if fetch_status == FetcherStatus.CANCELED:
                return Status.CANCELED
            elif fetch_status == FetcherStatus.FAILED:
                return Status.FAILED
            elif fetch_status == FetcherStatus.PENDING:
                return Status.PENDING
            elif fetch_status == FetcherStatus.RUNNING:
                return Status.RUNNING
        return Status.SUCCEEDED

    def handle_event(self, event: FetcherBenchmarkEvent, kafka_service: KafkaService):
        def extract_datasets(event) -> List[DataSet]:
            return event.payload.datasets

        def execute(task: DataSet, callback) -> None:

            task.dst = get_dataset_dst(task, self.s3_data_set_bucket)

            kafka_service.send_status_message_event(event, Status.PENDING, f"Dataset {task} sent to fetch")

            self.data_set_mgr.fetch(task, event, callback)

        def execute_all(tasks: List[DataSet], callback: Callable) -> None:
            kafka_service.send_status_message_event(event, Status.PENDING, "Start fetching datasets")

            pending = list(tasks)

            def on_done(data_set: DataSet):
                kafka_service.send_status_message_event(event, Status.PENDING, f"Dataset {data_set} processed")

                pending.remove(data_set)
                if not pending:
                    callback()

            for tsk in tasks:
                execute(tsk, on_done)

        tasks = extract_datasets(event)
        tasks = list(filter(lambda t: not t.dst, tasks))

        if not tasks:
            kafka_service.send_status_message_event(event, Status.SUCCEEDED, "Nothing to fetch")
            kafka_service.send_event(event, self.producer_topic)
            return

        def on_all_done():
            kafka_service.send_event(event, self.producer_topic)
            total_status = FetcherEventHandler._collect_status(event.payload.datasets)
            kafka_service.send_status_message_event(event, total_status, "All data sets processed")

        execute_all(tasks, on_all_done)

    def cleanup(self):
        self.data_set_mgr.stop()


class DataSetCmdObject:
    def __init__(self, data_set_mgr: DataSetManager):
        self.data_set_mgr = data_set_mgr

    def delete(self, client_id: str, target_action_id: str):
        self.data_set_mgr.cancel(client_id, target_action_id)


def create_fetcher_dispatcher(common_kafka_cfg: KafkaServiceConfig, fetcher_cfg: FetcherServiceConfig) -> KafkaService:
    data_set_mgr = create_data_set_manager(
        fetcher_cfg.zookeeper_ensemble_hosts, fetcher_cfg.kubeconfig, fetcher_cfg.fetcher_job
    )
    data_set_mgr.start()

    callbacks = {
        common_kafka_cfg.consumer_topic: [
            FetcherEventHandler(common_kafka_cfg.producer_topic, data_set_mgr, fetcher_cfg.s3_data_set_bucket)
        ],
        common_kafka_cfg.cmd_submit_topic: [
            KafkaCommandCallback(DataSetCmdObject(data_set_mgr), common_kafka_cfg.cmd_return_topic)
        ],
    }

    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, SERVICE_NAME)

    pod_name = get_pod_name()

    return KafkaService(
        name=SERVICE_NAME,
        version=__version__,
        callbacks=callbacks,
        kafka_consumer=consumer,
        kafka_producer=producer,
        pod_name=pod_name,
        status_topic=common_kafka_cfg.status_topic,
    )
