from typing import Tuple

import kubernetes

from bai_kafka_utils.events import ExecutorBenchmarkEvent, Status
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name
from bai_watcher import SERVICE_NAME, __version__, service_logger
from bai_watcher.args import WatcherServiceConfig
from bai_watcher.kubernetes_job_watcher import KubernetesJobWatcher, load_kubernetes_config
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

logger = service_logger.getChild(__name__)


def choose_status_from_benchmark_status(job_status: BenchmarkJobStatus) -> Tuple[Status, str]:
    if job_status in (
        BenchmarkJobStatus.FAILED_AT_SIDECAR_CONTAINER,
        BenchmarkJobStatus.FAILED_AT_BENCHMARK_CONTAINER,
        BenchmarkJobStatus.FAILED_AT_INIT_CONTAINERS,
    ):
        return Status.FAILED, "Job failed"
    elif job_status == BenchmarkJobStatus.SUCCEEDED:
        return Status.SUCCEEDED, "Job finished with success"
    elif job_status == BenchmarkJobStatus.NO_POD_SCHEDULED:
        return Status.FAILED, "Job was not able to run in the cluster"
    elif job_status == BenchmarkJobStatus.JOB_DOES_NOT_EXIST:
        return Status.PENDING, "Job is being created"
    elif job_status in (
        BenchmarkJobStatus.PENDING_AT_INIT_CONTAINERS,
        BenchmarkJobStatus.PENDING_AT_BENCHMARK_CONTAINER,
        BenchmarkJobStatus.PENDING_AT_SIDECAR_CONTAINER,
        BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS,
    ):
        return Status.PENDING, "Job is pending initialization"
    elif job_status in (BenchmarkJobStatus.PENDING_NODE_SCALING,):
        return Status.PENDING, "Job is pending nodes to scale"
    elif job_status == BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS:
        return Status.RUNNING, "Job is running"
    else:
        # All values of BenchmarkJobStatus must be handled
        assert False, f"Unknown status: {job_status}"


class WatchJobsEventHandler(KafkaServiceCallback):
    MESSAGE_METRICS_AVAILABLE = "Metrics available for job {action_id} at {results_url}"

    def __init__(self, config: WatcherServiceConfig):
        self.config = config
        self.watchers = {}

        load_kubernetes_config(config.kubeconfig)

    def handle_event(self, event: ExecutorBenchmarkEvent, kafka_service: KafkaService):
        job_id = event.payload.job.id
        if job_id in self.watchers:
            # This shouldn't happen, so it is here more as a protection mechanism
            logger.warning("There is already a watcher for job '%s'", job_id)
            return

        logger.info("Starting to watch the job '%s'", job_id)

        def callback(job_id, benchmark_job_status: BenchmarkJobStatus):
            # This method is called at each thread (not the Main Thread)
            logger.info(f"Benchmark job '{job_id}'' has status '{benchmark_job_status}'")
            status, message = choose_status_from_benchmark_status(benchmark_job_status)
            kafka_service.send_status_message_event(event, status, message)
            if benchmark_job_status == BenchmarkJobStatus.SUCCEEDED:
                kafka_service.send_status_message_event(
                    event, status.METRICS_AVAILABLE, self._get_metrics_available_message(event)
                )
            if benchmark_job_status is not None and benchmark_job_status.is_final():
                del self.watchers[job_id]
                logger.info(f"Job {job_id} is not being watched anymore")
                return True
            return False

        watcher = KubernetesJobWatcher(
            job_id,
            callback,
            kubernetes_client_jobs=kubernetes.client.BatchV1Api(),
            kubernetes_client_pods=kubernetes.client.CoreV1Api(),
            kubernetes_namespace=self.config.kubernetes_namespace_of_running_jobs,
        )
        self.watchers[job_id] = watcher
        watcher.start()

    def cleanup(self):
        pass

    def _get_metrics_available_message(self, event: ExecutorBenchmarkEvent):
        client_id = event.client_id
        action_id = event.action_id
        grafana_url = self.config.grafana_results_url.format(
            grafana_endpoint=self.config.grafana_endpoint,
            dashboard_id=self.config.grafana_op_metrics_dashboard_uid,
            client_id=client_id,
            action_id=action_id,
        )
        return self.MESSAGE_METRICS_AVAILABLE.format(action_id=action_id, results_url=grafana_url)


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
