import time
from typing import Callable, Tuple

import boto3
import kubernetes
from bai_kafka_utils.events import ExecutorBenchmarkEvent, Status
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name
from bai_kafka_utils.executors.descriptor import BenchmarkDescriptor, DistributedStrategy

from bai_watcher import SERVICE_NAME, __version__, service_logger
from bai_watcher.args import WatcherServiceConfig
from bai_watcher.kubernetes_job_watcher import KubernetesJobWatcher, load_kubernetes_config
from bai_watcher.sage_maker_job_watcher import SageMakerTrainingJobWatcher
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

logger = service_logger.getChild(__name__)


def choose_status_from_benchmark_status(job_status: BenchmarkJobStatus) -> Tuple[Status, str]:
    if job_status in (BenchmarkJobStatus.FAILED_AT_SIDECAR_CONTAINER, BenchmarkJobStatus.FAILED_AT_INIT_CONTAINERS):
        return Status.FAILED, "Benchmark failed"
    elif job_status == BenchmarkJobStatus.FAILED_AT_BENCHMARK_CONTAINER:
        return Status.FAILED, "Benchmark container failed - Please check your container"
    elif job_status == BenchmarkJobStatus.FAILED:
        return Status.FAILED, "Benchmark failed for an unknown reason"
    elif job_status == BenchmarkJobStatus.SUCCEEDED:
        return Status.SUCCEEDED, "Benchmark finished successfully"
    elif job_status == BenchmarkJobStatus.NO_POD_SCHEDULED:
        return Status.FAILED, "Benchmark was unable to run on the cluster"
    elif job_status == BenchmarkJobStatus.JOB_NOT_FOUND:
        return Status.CANCELED, "Benchmark cancelled - watch ended"
    elif job_status in (
        BenchmarkJobStatus.PENDING_AT_INIT_CONTAINERS,
        BenchmarkJobStatus.PENDING_AT_BENCHMARK_CONTAINER,
        BenchmarkJobStatus.PENDING_AT_SIDECAR_CONTAINER,
        BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS,
    ):
        return Status.PENDING, "Benchmark pending pod initialization"
    elif job_status in (BenchmarkJobStatus.PENDING_NODE_SCALING,):
        return Status.PENDING, "Benchmark pending node autoscaling"
    elif job_status == BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS:
        return Status.RUNNING, "Benchmark running"
    # SageMaker status messages
    elif job_status == BenchmarkJobStatus.SM_IN_PROGRESS_STARTING:
        return Status.PENDING, "Benchmark starting"
    elif job_status == BenchmarkJobStatus.SM_IN_PROGRESS_LAUNCHING_ML_INSTANCES:
        return Status.PENDING, "Launching ML instances"
    elif job_status == BenchmarkJobStatus.SM_IN_PROGRESS_PREP_TRAINING_STACK:
        return Status.PENDING, "Preparing training stack"
    elif job_status == BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING:
        return Status.PENDING, "Downloading data"
    elif job_status == BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING_TRAINING_IMG:
        return Status.PENDING, "Downloading benchmark image"
    elif job_status == BenchmarkJobStatus.SM_IN_PROGRESS_TRAINING:
        return Status.PENDING, "Benchmark running"
    elif job_status == BenchmarkJobStatus.SM_IN_PROGRESS_UPLOADING:
        return Status.PENDING, "Uploading data"
    elif job_status == BenchmarkJobStatus.SM_STOPPING:
        return Status.PENDING, "Benchmark stopping"
    elif job_status == BenchmarkJobStatus.SM_STOPPED:
        return Status.FAILED, "Benchmark stopped"
    elif job_status == BenchmarkJobStatus.SM_FAILED_MAX_RUNTIME_EXCEEDED:
        return Status.FAILED, "Benchmark failed - Max runtime exceeded"
    elif job_status == BenchmarkJobStatus.SM_FAILED_MAX_WAITTIME_EXCEEDED:
        return Status.FAILED, "Benchmark failed - Max wait time exceeded"
    elif job_status == BenchmarkJobStatus.SM_INTERRUPTED:
        return Status.FAILED, "Benchmark interrupted"
    elif job_status == BenchmarkJobStatus.SUCCEEDED:
        return Status.SUCCEEDED, "Benchmark finished successfully"
    elif BenchmarkJobStatus.SM_UNKNOWN:
        return Status.FAILED, "Benchmark reached unknown state - Please contact your system administrator"
    else:
        # All values of BenchmarkJobStatus must be handled
        assert False, f"Unknown status: {job_status}"


class WatchJobsEventHandler(KafkaServiceCallback):
    MESSAGE_METRICS_AVAILABLE = "Metrics available for job {action_id} at {results_url}"

    def __init__(self, config: WatcherServiceConfig):
        self.config = config
        self.watchers = {}

        load_kubernetes_config(config.kubeconfig)

    def _make_status_callback(
        self, event: ExecutorBenchmarkEvent, kafka_service: KafkaService, is_k8s_job: bool = True
    ) -> Callable[[str, BenchmarkJobStatus, KubernetesJobWatcher], bool]:
        job_start_time = None

        def callback(job_id, benchmark_job_status: BenchmarkJobStatus):
            nonlocal job_start_time

            # This method is called at each thread (not the Main Thread)
            logger.info(f"Benchmark job '{job_id}'' has status '{benchmark_job_status}'")
            status, message = choose_status_from_benchmark_status(benchmark_job_status)
            kafka_service.send_status_message_event(event, status, message)

            # TODO: Remove this once we know where to get the SM metrics from
            if is_k8s_job:
                if benchmark_job_status.is_running() and not job_start_time:
                    job_start_time = int(time.time() * 1000)
                    msg = self._get_metrics_available_message(event, job_start_time)
                    kafka_service.send_status_message_event(event, Status.METRICS_AVAILABLE, msg)

                if benchmark_job_status == BenchmarkJobStatus.SUCCEEDED:
                    job_end_time = int(time.time() * 1000)
                    msg = self._get_metrics_available_message(event, job_start_time, job_end_time)
                    kafka_service.send_status_message_event(event, Status.METRICS_AVAILABLE, msg)

            if benchmark_job_status is not None and benchmark_job_status.is_final():
                del self.watchers[job_id]
                logger.info(f"Job {job_id} is not being watched anymore")
                kafka_service.send_status_message_event(event, status, "No longer watching benchmark")
                return True
            return False

        return callback

    @staticmethod
    def _is_sage_maker_job(event: ExecutorBenchmarkEvent) -> bool:
        execution_engine = event.payload.toml.contents.get("info", {}).get("execution_engine", None)
        return execution_engine == "aws.sagemaker"

    def handle_event(self, event: ExecutorBenchmarkEvent, kafka_service: KafkaService):
        job_id = event.payload.job.id
        if job_id in self.watchers:
            # This shouldn't happen, so it is here more as a protection mechanism
            logger.warning("There is already a watcher for job '%s'", job_id)
            return

        descriptor = BenchmarkDescriptor.from_dict(event.payload.toml.contents)
        if descriptor.custom_params and descriptor.custom_params.merge is True:
            logger.info("Sagemaker training-jobs with metric merging are not yet supported by the watcher")
            kafka_service.send_status_message_event(
                event,
                Status.PENDING,
                "Sagemaker training-jobs with metric merging enabled are not yet supported by the watcher.",
            )
            return
        if descriptor.hardware.strategy not in [DistributedStrategy.SINGLE_NODE, DistributedStrategy.INFERENCE]:
            logger.info(f"Unsupported strategy {descriptor.hardware.strategy}")
            kafka_service.send_status_message_event(
                event, Status.PENDING, f"'{descriptor.hardware.strategy.value}' strategy is not currently supported."
            )
            return

        logger.info("Starting to watch the job '%s'", job_id)

        watcher_callback = self._make_status_callback(event, kafka_service, not self._is_sage_maker_job(event))

        if self._is_sage_maker_job(event):
            watcher = SageMakerTrainingJobWatcher(
                job_id=event.action_id, callback=watcher_callback, sagemaker_client=boto3.client("sagemaker")
            )
            kafka_service.send_status_message_event(event, Status.PENDING, "Watching SageMaker benchmark")
        else:
            watcher = KubernetesJobWatcher(
                job_id,
                watcher_callback,
                kubernetes_client_jobs=kubernetes.client.BatchV1Api(),
                kubernetes_client_pods=kubernetes.client.CoreV1Api(),
                kubernetes_namespace=self.config.kubernetes_namespace_of_running_jobs,
            )
            kafka_service.send_status_message_event(event, Status.PENDING, "Watching Kubernetes benchmark")
        self.watchers[job_id] = watcher
        watcher.start()

    def cleanup(self):
        pass

    def _get_metrics_available_message(
        self, event: ExecutorBenchmarkEvent, job_start_time: int, job_end_time: int = None
    ):
        client_id = event.client_id
        action_id = event.action_id

        if job_end_time is None:
            # If no end timestamp is provided, adjust the X-axis to 1h by default
            job_end_time = job_start_time + (60 * 60 * 1000)

        grafana_url = self.config.grafana_results_url.format(
            grafana_endpoint=self.config.grafana_endpoint,
            dashboard_id=self.config.grafana_op_metrics_dashboard_uid,
            client_id=client_id,
            action_id=action_id,
            start_tstamp=job_start_time,
            end_tstamp=job_end_time,
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
