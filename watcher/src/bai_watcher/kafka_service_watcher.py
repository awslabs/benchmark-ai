import logging

import kubernetes

from bai_kafka_utils.events import ExecutorBenchmarkEvent, Status
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_watcher import SERVICE_NAME, __version__
from bai_watcher.args import WatcherServiceConfig
from bai_watcher.kubernetes_job_watcher import KubernetesJobWatcher, KubernetesJobStatus, load_kubernetes_config

logger = logging.getLogger(__name__)


class WatchJobsEventHandler(KafkaServiceCallback):
    def __init__(self, config: WatcherServiceConfig):
        self.config = config
        self.watchers = {}

        load_kubernetes_config(config.kubeconfig)
        self.kubernetes_clients = {"single-node": kubernetes.client.BatchV1Api()}

    def handle_event(self, event: ExecutorBenchmarkEvent, kafka_service: KafkaService):
        def notify_job_status(job_id, job_status: KubernetesJobStatus):
            # This method is called at each thread (not the Main Thread)
            logger.info(f"Job '{job_id}'' has status '{job_status}'")

            if job_status is None:
                # Job does not exist, it might have been already deleted by the collector, we can safely ignore this
                # status
                pass
            elif job_status == KubernetesJobStatus.FAILED:
                kafka_service.send_status_message_event(event, Status.FAILED, "Job failed")
            elif job_status == KubernetesJobStatus.RUNNING:
                kafka_service.send_status_message_event(event, Status.RUNNING, "Job is running")
            elif job_status == KubernetesJobStatus.SUCCEEDED:
                kafka_service.send_status_message_event(event, Status.SUCCEEDED, "Job finished with success")

            else:
                raise ValueError(f"Unknown status: {job_status}")

            if job_status != KubernetesJobStatus.RUNNING:
                del self.watchers[job_id]
                logger.info(f"Job {job_id} is not being watched anymore")
                return True
            return False

        job_id = event.payload.job.id
        if job_id in self.watchers:
            # This shouldn't happen, so it is here more as a protection mechanism
            logger.warning("There is already a watcher for job '%s'", job_id)
            return

        logger.info("Starting to watch the job '%s'", job_id)
        kubernetes_client = self.kubernetes_clients["single-node"]
        watcher = KubernetesJobWatcher(
            job_id,
            notify_job_status,
            kubernetes_client=kubernetes_client,
            kubernetes_namespace=self.config.kubernetes_namespace_of_running_jobs,
        )
        self.watchers[job_id] = watcher
        watcher.start()

    def cleanup(self):
        pass


def create_service(common_kafka_cfg: KafkaServiceConfig, service_cfg: WatcherServiceConfig) -> KafkaService:
    callbacks = [WatchJobsEventHandler(service_cfg)]
    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, ExecutorBenchmarkEvent)
    return KafkaService(
        SERVICE_NAME,
        __version__,
        common_kafka_cfg.producer_topic,
        callbacks,
        consumer,
        producer,
        status_topic=common_kafka_cfg.status_topic,
    )
