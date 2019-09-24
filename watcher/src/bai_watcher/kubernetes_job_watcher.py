from __future__ import annotations

import itertools
import time
from pathlib import Path
from threading import Thread
from typing import Callable, Tuple, Optional

import kubernetes
from kubernetes.client import V1Job, V1JobStatus, V1PodList, BatchV1Api, CoreV1Api

from bai_watcher import service_logger
from bai_watcher.status_inferrers.single_node import SingleNodeStrategyKubernetesStatusInferrer
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

logger = service_logger.getChild(__name__)

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
    def __init__(
        self,
        job_id: str,
        callback: Callable[[str, BenchmarkJobStatus, KubernetesJobWatcher], bool],
        *,
        kubernetes_namespace: str,
        kubernetes_client_jobs: BatchV1Api,
        kubernetes_client_pods: CoreV1Api,
    ):
        self.job_id = job_id
        self.callback = callback
        self.kubernetes_namespace = kubernetes_namespace
        self.jobs_client = kubernetes_client_jobs
        self.pod_client = kubernetes_client_pods
        self.thread = Thread(target=self._thread_run_loop, daemon=True, name=f"k8s-job-watcher-{job_id}")
        self.job_start_time = None
        self.metrics_available_message_sent = False

        # Run result variables
        self._success = None
        self._error = None

    def start(self):
        self.thread.start()

    def wait(self):
        self.thread.join()

    def get_result(self) -> Tuple[Optional[bool], Optional[Exception]]:
        return self._success, self._error

    def get_status(self):
        try:
            k8s_job: V1Job = self.jobs_client.read_namespaced_job_status(self.job_id, self.kubernetes_namespace)
        except kubernetes.client.rest.ApiException as e:
            if e.status == 404:
                return BenchmarkJobStatus.JOB_NOT_FOUND

            logger.exception(
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

        if status.is_running() and self.job_start_time is None:
            self.job_start_time = int(time.time() * 1000)

        return status

    def _thread_run_loop(self):
        # Use itertools.count() so that tests can mock the infinite loop
        for _ in itertools.count():
            try:
                status = self.get_status()
                stop_watching = self.callback(self.job_id, status, self)
                if stop_watching:
                    self._success = True
                    return
            except Exception as err:
                logger.exception("Watcher loop failed with uncaught exception")
                self._success = False
                self._error = err
                return
            time.sleep(SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS)
