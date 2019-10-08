import logging
from functools import wraps
from time import sleep
from typing import Callable

import kubernetes
from kubernetes.client import V1Pod, V1PodStatus
from kubernetes.client import V1PodList, V1PersistentVolumeClaimList, V1beta1CronJobList, V1JobList, V1ServiceList
from timeout_decorator import timeout

from bai_k8s_utils.service_labels import ServiceLabels

logger = logging.getLogger(__name__)

K8SBaiPredicate = Callable[[str, str, str], bool]


def negate(f):
    @wraps(f)
    def g(*args, **kwargs):
        return not f(*args, **kwargs)

    return g


class KubernetesTestUtilsClient:
    # Utilities to use in integration tests.
    # All of them expect pod to be at least in Pending state.
    # So no super long timeouts are necessary for any environment
    # Although we seen 10 seconds to be not enough to _terminate_ the pod
    def __init__(self, api_client: kubernetes.client.ApiClient, service: str):
        self.batch_api_instance = kubernetes.client.BatchV1Api(api_client)
        self.core_api_instance = kubernetes.client.CoreV1Api(api_client)
        self.beta_api_instance = kubernetes.client.BatchV1beta1Api(api_client)
        self.service = service

    DEFAULT_TIMEOUT_SECONDS = 60

    def is_pod_present(self, namespace: str, client_id: str, action_id: str):
        pods = self._get_pods(namespace, client_id, action_id)
        return bool(pods.items)

    def _get_pods(self, namespace, client_id, action_id) -> V1PodList:
        label_selector = ServiceLabels.get_label_selector(self.service, client_id, action_id)
        logger.info(f"pod selector request:{label_selector}")
        pods = self.core_api_instance.list_namespaced_pod(namespace, label_selector=label_selector)
        return pods

    def is_pod_succeeded(self, namespace: str, client_id: str, action_id: str):
        pods = self._get_pods(namespace, client_id, action_id)
        if len(pods.items) == 0:
            return False
        if len(pods.items) > 1:
            raise ValueError("Multiple pods found, but one expected")
        pod: V1Pod = pods.items[0]
        status: V1PodStatus = pod.status
        return status.phase == "Succeeded"

    def is_job_present(self, namespace: str, client_id: str, action_id: str):
        label_selector = ServiceLabels.get_label_selector(self.service, client_id, action_id)
        logger.info(f"job selector request:{label_selector}")
        pods: V1PodList = self.batch_api_instance.list_namespaced_job(namespace, label_selector=label_selector)
        return bool(pods.items)

    def is_cron_job_present(self, namespace: str, client_id: str, action_id: str):
        label_selector = ServiceLabels.get_label_selector(self.service, client_id, action_id)
        logger.info(f"cron job selector request:{label_selector}")
        cron_jobs: V1beta1CronJobList = self.beta_api_instance.list_namespaced_cron_job(
            namespace, label_selector=label_selector
        )
        return bool(cron_jobs.items)

    def is_inference_jobs_present(self, namespace: str, client_id: str, action_id: str):
        label_selector = ServiceLabels.get_label_selector(self.service, client_id, action_id)
        logger.info(f"job selector request:{label_selector}")
        job_list: V1JobList = self.batch_api_instance.list_namespaced_job(namespace, label_selector=label_selector)
        return len(job_list.items) == 2

    def if_service_present(self, namespace: str, client_id: str, action_id: str):
        label_selector = ServiceLabels.get_label_selector(self.service, client_id, action_id)
        logger.info(f"service selector request:{label_selector}")
        services: V1ServiceList = self.core_api_instance.list_namespaced_service(
            namespace, label_selector=label_selector
        )
        return bool(services.items)

    def is_inference_benchmark_client_succeeded(self, namespace: str, client_id: str, action_id: str):
        pods = self._get_pods(namespace, client_id, action_id)
        client_pod = list(filter(lambda pod: pod.metadata.name.startswith(f"b-{action_id}".lower()), pods.items))
        if len(client_pod) == 0:
            raise ValueError("Inference benchmark client pod not found")
        logger.info(f"Found {len(client_pod)} client pods")
        logger.info(f"Status {client_pod[0]}")
        return client_pod[0].status.phase == "Succeeded"

    def is_volume_claim_present(self, namespace: str, client_id: str, action_id: str):
        label_selector = ServiceLabels.get_label_selector(self.service, client_id, action_id)
        logger.info(f"volume claim selector request:{label_selector}")
        pods: V1PersistentVolumeClaimList = self.core_api_instance.list_namespaced_persistent_volume_claim(
            namespace, label_selector=label_selector
        )
        return bool(pods.items)

    def _wait_loop(
        self,
        predicate: K8SBaiPredicate,
        msg: str,
        namespace: str,
        client_id: str,
        action_id: str,
        duration: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        @timeout(duration)
        def fn():
            while predicate(namespace, client_id, action_id):
                logger.info(msg)
                sleep(1)

        fn()

    def wait_for_service_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(negate(self.if_service_present), "service doesn't exist yet", namespace, client_id, action_id)

    def wait_for_service_not_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(self.if_service_present, "service still exists", namespace, client_id, action_id)

    def wait_for_volume_claim_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(
            negate(self.is_volume_claim_present), "volume claim doesn't exist yet", namespace, client_id, action_id
        )

    def wait_for_volume_claim_not_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(self.is_volume_claim_present, "volume claim still exists", namespace, client_id, action_id)

    def wait_for_pod_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(negate(self.is_pod_present), "pod doesn't exist yet", namespace, client_id, action_id)

    def wait_for_pod_succeeded(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(negate(self.is_pod_succeeded), "pod has not succeeded yet", namespace, client_id, action_id)

    def wait_for_pod_not_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(self.is_pod_present, "pod still exists", namespace, client_id, action_id)

    def wait_for_job_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(negate(self.is_job_present), "job doesn't exist yet", namespace, client_id, action_id)

    def wait_for_job_not_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(self.is_job_present, "job still exists", namespace, client_id, action_id)

    def wait_for_cron_job_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(negate(self.is_cron_job_present), "cron job doesn't exist yet", namespace, client_id, action_id)

    def wait_for_cron_job_not_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(self.is_cron_job_present, "cron job still exists", namespace, client_id, action_id)

    def wait_for_inference_jobs_exists(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(
            negate(self.is_inference_jobs_present),
            "inference benchmark jobs dont't exist yet",
            namespace,
            client_id,
            action_id,
        )

    def wait_for_inference_benchmark_client_succeeded(self, namespace: str, client_id: str, action_id: str):
        self._wait_loop(
            negate(self.is_inference_benchmark_client_succeeded),
            "inference benchmark client has not succeeded yet",
            namespace,
            client_id,
            action_id,
        )
