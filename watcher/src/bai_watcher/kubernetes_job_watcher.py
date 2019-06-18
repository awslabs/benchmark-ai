import logging

import itertools
import kubernetes
import time
from kubernetes.client import V1Job, V1JobStatus, V1PodList
from pathlib import Path
from threading import Thread

from bai_watcher.status_inferrers.single_node import SingleNodeStrategyKubernetesStatusInferrer

logger = logging.getLogger(__name__)

SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS = 5


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


class KubernetesJobWatcher:
    def __init__(self, job_id, callback, *, kubernetes_namespace, kubernetes_client_jobs, kubernetes_client_pods):
        self.job_id = job_id
        self.callback = callback
        self.kubernetes_namespace = kubernetes_namespace
        self.jobs_client = kubernetes_client_jobs
        self.pod_client = kubernetes_client_pods
        self.thread = Thread(target=self._thread_run_loop, daemon=True, name=f"k8s-job-watcher-{job_id}")

    def start(self):
        self.thread.start()

    def get_status(self):
        try:
            k8s_job: V1Job = self.jobs_client.read_namespaced_job_status(self.job_id, self.kubernetes_namespace)
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
        logger.debug(f"[job-id: {self.job_id}] Kubernetes Job status: {k8s_job_status}")
        logger.debug(f"[job-id: {self.job_id}] Kubernetes Job conditions: {k8s_job_status.conditions}")

        pods: V1PodList = self.pod_client.list_namespaced_pod(
            self.kubernetes_namespace, label_selector=f"job-name={self.job_id}"
        )
        logger.debug(f"[job-id: {self.job_id}] Kubernetes Job pods: {pods}")
        inferrer = SingleNodeStrategyKubernetesStatusInferrer(k8s_job_status, pods.items)
        status = inferrer.status()
        return status

    def _thread_run_loop(self):
        # Use itertools.count() so that tests can mock the infinite loop
        for _ in itertools.count():
            status = self.get_status()
            stop_watching = self.callback(self.job_id, status)
            if stop_watching:
                return
            time.sleep(SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS)
