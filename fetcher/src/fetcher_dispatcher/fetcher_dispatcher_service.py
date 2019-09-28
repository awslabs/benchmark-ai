import logging
from typing import List, Callable, Optional, Any

from bai_kafka_utils.cmd_callback import KafkaCommandCallback
from bai_kafka_utils.events import CommandRequestEvent, FetcherBenchmarkEvent, Status, FetcherStatus
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name
from bai_zk_utils.zk_locker import DistributedRWLockManager
from kazoo.client import KazooClient

from fetcher_dispatcher import SERVICE_NAME, __version__
from fetcher_dispatcher.args import FetcherServiceConfig, FetcherJobConfig
from fetcher_dispatcher.data_set_manager import DownloadableContent, DataSetManager, get_lock_name
from fetcher_dispatcher.data_set_pull import get_dataset_dst
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher

LOCK_MANAGER_PREFIX = "fetcher_lock_manager"

logger = logging.getLogger(__name__)


def create_data_set_manager(zookeeper_ensemble_hosts: str, kubeconfig: str, fetcher_job: FetcherJobConfig):
    zk_client = KazooClient(zookeeper_ensemble_hosts)
    job_dispatcher = KubernetesDispatcher(SERVICE_NAME, kubeconfig, zookeeper_ensemble_hosts, fetcher_job)

    lock_manager = DistributedRWLockManager(zk_client, LOCK_MANAGER_PREFIX, get_lock_name)

    return DataSetManager(zk_client, job_dispatcher, lock_manager)


class FetcherEventHandler(KafkaServiceCallback):
    def __init__(self, producer_topic: str, data_set_mgr: DataSetManager, s3_data_set_bucket: str):
        self.data_set_mgr = data_set_mgr
        self.s3_data_set_bucket = s3_data_set_bucket
        self.producer_topic = producer_topic

    @staticmethod
    def _collect_status(data_sets: List[DownloadableContent]) -> Status:
        fetch_statuses = {d.status for d in data_sets}
        if FetcherStatus.CANCELED in fetch_statuses:
            return Status.CANCELED
        if FetcherStatus.FAILED in fetch_statuses:
            return Status.FAILED
        # These 2 cases should never happen
        if FetcherStatus.PENDING in fetch_statuses:
            return Status.PENDING
        if FetcherStatus.RUNNING in fetch_statuses:
            return Status.RUNNING
        return Status.SUCCEEDED

    def handle_event(self, event: FetcherBenchmarkEvent, kafka_service: KafkaService):
        def extract_datasets(event) -> List[DownloadableContent]:
            return event.payload.datasets

        def execute(task: DownloadableContent, callback) -> None:

            task.dst = get_dataset_dst(task, self.s3_data_set_bucket)

            kafka_service.send_status_message_event(event, Status.PENDING, f"Dataset {task.src} sent to fetch")

            self.data_set_mgr.fetch(task, event, callback)

        def execute_all(tasks: List[DownloadableContent], callback: Callable) -> None:
            kafka_service.send_status_message_event(event, Status.PENDING, "Initiating dataset download...")

            pending = list(tasks)

            def on_done(data_set: DownloadableContent):
                if data_set.status == FetcherStatus.DONE:
                    msg, status = f"Dataset {data_set.src} downloaded...", Status.PENDING
                elif data_set.status == FetcherStatus.CANCELED:
                    msg, status = f"Dataset {data_set.src} download canceled...", Status.CANCELED
                elif data_set.status == FetcherStatus.FAILED:
                    msg, status = f"Dataset {data_set.src} download failed: '{data_set.message}'...", Status.FAILED
                elif data_set.status in {FetcherStatus.RUNNING, FetcherStatus.PENDING}:
                    msg, status = f"Downloading dataset {data_set.src}...", Status.PENDING
                else:
                    msg, status = f"Unknown status {data_set.status} issued for dataset {data_set.src}", Status.ERROR

                if msg and status:
                    kafka_service.send_status_message_event(event, status, msg)

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
            total_status = FetcherEventHandler._collect_status(event.payload.datasets)
            # Any failed/canceled fetching is not actionable - so we don't send it down the pipeline
            if total_status == Status.SUCCEEDED:
                kafka_service.send_event(event, self.producer_topic)
                kafka_service.send_status_message_event(event, total_status, "All data sets processed")
            elif total_status in [Status.CANCELED, Status.FAILED]:
                kafka_service.send_status_message_event(event, total_status, "Aborting execution")
            else:
                logging.warning(f"Fetching ended with unexpected status: {total_status}")

        execute_all(tasks, on_all_done)

    def cleanup(self):
        self.data_set_mgr.stop()


class DataSetCmdObject:
    def __init__(self, data_set_mgr: DataSetManager):
        self.data_set_mgr = data_set_mgr

    def cancel(
        self,
        kafka_service: KafkaService,
        event: CommandRequestEvent,
        client_id: str,
        target_action_id: str,
        cascade: bool = False,
    ) -> Optional[Any]:

        kafka_service.send_status_message_event(event, Status.PENDING, "Canceling downloads...", target_action_id)
        try:
            k8s_delete_results, num_zk_nodes_updated = self.data_set_mgr.cancel(client_id, target_action_id)
        except Exception as err:
            kafka_service.send_status_message_event(
                event,
                Status.FAILED,
                f"An error occurred when attempting to delete resources related to {target_action_id}. "
                f"Please check the status of the deletion command ({event.action_id} "
                f"for additional information.",
                target_action_id,
            )
            raise err

        if num_zk_nodes_updated == 0:
            kafka_service.send_status_message_event(
                event, Status.SUCCEEDED, "No downloads to cancel...", target_action_id
            )

        return {"k8s_deletion_results": k8s_delete_results, "num_zookeeper_nodes_updated": num_zk_nodes_updated}


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
