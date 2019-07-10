from typing import Callable
import itertools
import kubernetes
import time
import logging

from kubernetes.client import V1Job, V1JobStatus, V1PodList, BatchV1Api, CoreV1Api, CustomObjectsApi
from pathlib import Path
from threading import Thread

from bai_watcher import service_logger
from bai_watcher.status_inferrers.horovod import HorovodStrategyKubernetesStatusInferrer
from bai_watcher.status_inferrers.single_node import SingleNodeStrategyKubernetesStatusInferrer
from bai_watcher.status_inferrers.status import BenchmarkJobStatus
from bai_k8s_utils.strategy import Strategy

logging.basicConfig(level="DEBUG")
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
        callback: Callable[[str, BenchmarkJobStatus], bool],
        strategy: Strategy,
        *,
        kubernetes_namespace: str,
        kubernetes_client_jobs: BatchV1Api,
        kubernetes_client_pods: CoreV1Api,
        kubernetes_client_crds: CustomObjectsApi,
    ):
        self.job_id = job_id
        self.callback = callback
        self.strategy = strategy
        self.kubernetes_namespace = kubernetes_namespace
        self.jobs_client = kubernetes_client_jobs
        self.pod_client = kubernetes_client_pods
        self.crds_client = kubernetes_client_crds
        self.thread = Thread(target=self._thread_run_loop, daemon=True, name=f"k8s-job-watcher-{job_id}")

    def start(self):
        self.thread.start()

    def get_status(self):
        if self.strategy == Strategy.SINGLE_NODE:
            try:
                k8s_job: V1Job = self.jobs_client.read_namespaced_job_status(self.job_id, self.kubernetes_namespace)
            except kubernetes.client.rest.ApiException as e:
                if e.status == 404:
                    logger.exception(
                        "The specified job {job_id} does not exist. Stopping thread.".format(job_id=self.job_id)
                    )
                    return BenchmarkJobStatus.JOB_DOES_NOT_EXIST

                logger.exception(
                    "Unknown error from Kubernetes, stopping thread that watches job {job_id} with an exception".format(
                        job_id=self.job_id
                    )
                )
                raise

            k8s_job_status: V1JobStatus = k8s_job.status
            logger.debug(f"[job-id: {self.job_id}] Kubernetes Job status: {k8s_job_status}")
            logger.debug(f"[job-id: {self.job_id}] Kubernetes Job conditions: {k8s_job_status.conditions}")
            label_selector = f"job-name={self.job_id}"
            inferrer_type = SingleNodeStrategyKubernetesStatusInferrer

        elif self.strategy == Strategy.HOROVOD:
            try:
                # TODO: Find a way to retrieve status of mpijobs, so we'll have to rely on inspecting pods instead
                # CustomObjectsAPI:
                # https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/CustomObjectsApi.md
                k8s_mpijob = self.crds_client.get_namespaced_custom_object(
                    group="kubeflow.org",
                    version="v1alpha1",
                    namespace=self.kubernetes_namespace,
                    plural="mpijobs",
                    name=self.job_id,
                )
            except kubernetes.client.rest.ApiException as e:
                pass

            k8s_job_status = k8s_mpijob.status
            label_selector = f"mpi_job_name={self.job_id}"
            inferrer_type = HorovodStrategyKubernetesStatusInferrer

        pods: V1PodList = self.pod_client.list_namespaced_pod(self.kubernetes_namespace, label_selector=label_selector)
        logger.debug(f"[job-id: {self.job_id}] Kubernetes Job pods: {pods}")
        inferrer = inferrer_type(k8s_job_status, pods.items)
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


# Leaving this code here as it is useful for testing
#
# job_id = "b-3a619d85-49dc-4000-9dd6-29422fa67432"
# callback = lambda: None
# strategy = Strategy.HOROVOD
# kubernetes_namespace = "default"
# os.environ["AWS_PROFILE"] = "jlcont"
# load_kubernetes_config()
# kubernetes_client_jobs = kubernetes.client.BatchV1Api()
# kubernetes_client_pods = CoreV1Api()
# kubernetes_client_crds = CustomObjectsApi()
# KubernetesJobWatcher(
#     job_id,
#     callback,
#     strategy,
#     kubernetes_namespace=kubernetes_namespace,
#     kubernetes_client_jobs=kubernetes_client_jobs,
#     kubernetes_client_pods=kubernetes_client_pods,
#     kubernetes_client_crds=kubernetes_client_crds,
# ).get_status()
