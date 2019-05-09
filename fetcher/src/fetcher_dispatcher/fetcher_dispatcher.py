from kazoo.client import KazooClient
from typing import List, Callable

from bai_kafka_utils.events import FetcherBenchmarkEvent, Status
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from fetcher_dispatcher import SERVICE_NAME, __version__
from fetcher_dispatcher.args import FetcherServiceConfig, FetcherJobConfig
from fetcher_dispatcher.data_set_manager import DataSet, DataSetManager
from fetcher_dispatcher.data_set_pull import get_dataset_dst
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher


def create_data_set_manager(zookeeper_ensemble_hosts: str, kubeconfig: str, fetcher_job: FetcherJobConfig):
    zk_client = KazooClient(zookeeper_ensemble_hosts)
    job_dispatcher = KubernetesDispatcher(kubeconfig, zookeeper_ensemble_hosts, fetcher_job)

    return DataSetManager(zk_client, job_dispatcher)


class FetcherEventHandler(KafkaServiceCallback):
    def __init__(self, data_set_mgr: DataSetManager, s3_data_set_bucket: str):
        self.data_set_mgr = data_set_mgr
        self.s3_data_set_bucket = s3_data_set_bucket

    def handle_event(self, event: FetcherBenchmarkEvent, kafka_service: KafkaService):
        def extract_datasets(event) -> List[DataSet]:
            return event.payload.datasets

        def execute(task: DataSet, callback) -> None:

            task.dst = get_dataset_dst(task.src, self.s3_data_set_bucket)

            kafka_service.send_status_message_event(event, Status.PENDING, f"Dataset {task} sent to fetch")

            self.data_set_mgr.fetch(task, callback)

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
            return event

        def on_all_done():
            kafka_service.send_event(event)
            kafka_service.send_status_message_event(event, Status.SUCCEEDED, "All data sets processed")

        execute_all(tasks, on_all_done)

    def cleanup(self):
        self.data_set_mgr.stop()


def create_fetcher_dispatcher(common_kafka_cfg: KafkaServiceConfig, fetcher_cfg: FetcherServiceConfig) -> KafkaService:
    data_set_mgr = create_data_set_manager(
        fetcher_cfg.zookeeper_ensemble_hosts, fetcher_cfg.kubeconfig, fetcher_cfg.fetcher_job
    )
    data_set_mgr.start()

    callbacks = [FetcherEventHandler(data_set_mgr, fetcher_cfg.s3_data_set_bucket)]

    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, FetcherBenchmarkEvent)

    return KafkaService(
        SERVICE_NAME,
        __version__,
        common_kafka_cfg.producer_topic,
        callbacks,
        consumer,
        producer,
        common_kafka_cfg.status_topic,
    )
