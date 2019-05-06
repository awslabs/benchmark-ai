import logging
import time
from enum import Enum
from threading import Thread
from kubernetes.client import V1Job, V1JobStatus
from pathlib import Path
import kubernetes


logger = logging.getLogger(__name__)

SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS = 5


class KubernetesJobStatus(Enum):
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"
    RUNNING = "RUNNING"


def load_kubernetes_config(kubeconfig=None):
    # TODO: Extract this logic to a common class for all projects
    if kubeconfig is not None:
        kubeconfig = Path(kubeconfig)
    else:
        kubeconfig = Path.home().joinpath(".bai", "kubeconfig")

    if kubeconfig.exists():
        logger.info(f"Loading kubeconfig from {kubeconfig}")
        kubernetes.config.load_kube_config(str(kubeconfig))
    else:
        logger.info(f"Loading kubeconfig from incluster")
        kubernetes.config.load_incluster_config()


class K8SJobWatcher:
    def __init__(self, job_id, callback, *, kubernetes_namespace, kubernetes_client):
        self.job_id = job_id
        self.callback = callback
        self.kubernetes_namespace = kubernetes_namespace
        self.kubernetes_client = kubernetes_client
        self.thread = Thread(target=self._thread_run_loop, daemon=True, name=f"k8s-job-watcher-{job_id}")

    def start(self):
        self.thread.start()

    def get_status(self):
        try:
            k8s_job: V1Job = self.kubernetes_client.read_namespaced_job_status(self.job_id, self.kubernetes_namespace)
        except kubernetes.client.rest.ApiException as e:
            if e.status == 404:
                logging.exception(
                    "The specified job {job_id} does not exist. Stopping thread.".format(job_id=self.job_id)
                )
                return None

            logging.exception(
                "Unknown error from Kubernetes, stopping thread that watches job {job_id} with an exception".format(
                    job_id=self.job_id
                )
            )
            raise

        k8s_job_status: V1JobStatus = k8s_job.status

        if k8s_job_status.failed == 1:
            return KubernetesJobStatus.FAILED
        if k8s_job_status.succeeded == 1:
            return KubernetesJobStatus.SUCCEEDED
        if k8s_job_status.active == 1:
            return KubernetesJobStatus.RUNNING
        raise ValueError(
            "Can't determine what is the job status from {} (there is a bug in the code), erroring the watcher".format(
                k8s_job_status
            )
        )

    def _thread_run_loop(self):
        self._running = True
        while self._running:
            status = self.get_status()
            stop_watching = self.callback(self.job_id, status)
            if stop_watching:
                return
            time.sleep(SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS)
