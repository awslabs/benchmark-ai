import logging
import kubernetes

from bai_kafka_utils.events import ExecutorBenchmarkEvent, Status
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name
from bai_watcher import SERVICE_NAME, __version__
from bai_watcher.args import WatcherServiceConfig
from bai_watcher.kubernetes_job_watcher import KubernetesJobWatcher, load_kubernetes_config
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

logger = logging.getLogger(__name__)


class WatchJobsEventHandler(KafkaServiceCallback):
    def __init__(self, config: WatcherServiceConfig):
        self.config = config
        self.watchers = {}

        load_kubernetes_config(config.kubeconfig)

    def handle_event(self, event: ExecutorBenchmarkEvent, kafka_service: KafkaService):
        def notify_job_status(job_id, job_status: BenchmarkJobStatus):
            # This method is called at each thread (not the Main Thread)
            logger.info(f"Job '{job_id}'' has status '{job_status}'")

            if job_status is None:
                # Job does not exist, it might have been already deleted by the collector, we can safely ignore this
                # status
                pass
            elif job_status in (
                BenchmarkJobStatus.FAILED_AT_SIDECAR_CONTAINER,
                BenchmarkJobStatus.FAILED_AT_BENCHMARK_CONTAINER,
                BenchmarkJobStatus.FAILED_AT_INIT_CONTAINERS,
            ):
                kafka_service.send_status_message_event(event, Status.FAILED, "Job failed")
            elif job_status == BenchmarkJobStatus.SUCCEEDED:
                kafka_service.send_status_message_event(event, Status.SUCCEEDED, "Job finished with success")
            elif job_status in (
                BenchmarkJobStatus.PENDING_AT_INIT_CONTAINERS,
                BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS,
            ):
                kafka_service.send_status_message_event(event, Status.PENDING, "Job is pending initialization")
            elif job_status in (BenchmarkJobStatus.PENDING_NODE_SCALING,):
                kafka_service.send_status_message_event(event, Status.PENDING, "Job is pending nodes to scale")
            elif job_status == BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS:
                kafka_service.send_status_message_event(event, Status.RUNNING, "Job is running")
            else:
                raise ValueError(f"Unknown status: {job_status}")

            if job_status.is_final():
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
        watcher = KubernetesJobWatcher(
            job_id,
            notify_job_status,
            kubernetes_client_jobs=kubernetes.client.BatchV1Api(),
            kubernetes_client_pods=kubernetes.client.CoreV1Api(),
            kubernetes_namespace=self.config.kubernetes_namespace_of_running_jobs,
        )
        self.watchers[job_id] = watcher
        watcher.start()

    def cleanup(self):
        pass


def create_service(common_kafka_cfg: KafkaServiceConfig, service_cfg: WatcherServiceConfig) -> KafkaService:
    callbacks = {common_kafka_cfg.consumer_topic: [WatchJobsEventHandler(service_cfg)]}
    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, SERVICE_NAME)
    return KafkaService(
        name=SERVICE_NAME,
        version=__version__,
        callbacks=callbacks,
        kafka_consumer=consumer,
        kafka_producer=producer,
        pod_name=get_pod_name(),
        status_topic=common_kafka_cfg.status_topic,
    )
