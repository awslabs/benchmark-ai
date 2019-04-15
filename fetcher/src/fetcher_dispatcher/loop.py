import logging

from kazoo.client import KazooClient
from typing import List, Callable

from bai_common.events import DataSet
from fetcher_dispatcher.data_set_manager import DataSetManager
from fetcher_dispatcher.data_set_pull import get_dataset_dst
from fetcher_dispatcher.kafka_client import create_kafka_producer, create_kafka_consumer
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher

logger = logging.getLogger(__name__)


def create_data_set_manager(zookeeper_ensemble_hosts: str, kubeconfig: str, fetcher_job_image: str):
    zk_client = KazooClient(zookeeper_ensemble_hosts)
    job_dispatcher = KubernetesDispatcher(kubeconfig, fetcher_job_image, zookeeper_ensemble_hosts)

    return DataSetManager(zk_client, job_dispatcher)


def run_msg_loop(args):
    data_set_mgr = create_data_set_manager(args.zookeeper_ensemble_hosts, args.kubeconfig, args.fetcher_job_image)
    data_set_mgr.start()

    producer = create_kafka_producer(args.bootstrap_servers)

    def safe_handle_msg(msg):
        try:
            handle_msg(msg)
        except:
            logger.exception("Failed to handle message: %s", msg)

    def handle_msg(msg):
        if not msg.value:
            logger.debug("Ignoring empty message")
            return
        logger.debug("Got event %s", msg)

        def extract_data_sets(msg) -> List[DataSet]:
            return msg.value.payload.data_sets

        def execute(task: DataSet, callback) -> None:
            task.dst = get_dataset_dst(task.src, args.s3_data_set_bucket)

            data_set_mgr.fetch(task, callback)

        def execute_all(tasks: List[DataSet], callback: Callable) -> None:

            pending = list(tasks)

            def on_done(data_set: DataSet):
                pending.remove(data_set)
                if not pending:
                    callback()

            for tsk in tasks:
                execute(tsk, on_done)

        tasks = extract_data_sets(msg)
        tasks = list(filter(lambda t: not t.dst, tasks))

        if not tasks:
            return

        def on_all_done():
            producer.send(args.producer_topic, value=msg.value)

        execute_all(tasks, on_all_done)

    consumer = create_kafka_consumer(args.bootstrap_servers, args.consumer_group_id, args.consumer_topic)
    for msg in consumer:
        safe_handle_msg(msg)
