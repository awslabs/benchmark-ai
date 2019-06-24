from time import sleep

import kubernetes
from kubernetes.client import V1PodList

from fetcher_dispatcher import SERVICE_NAME
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher


class KubernetesTestUtilsClient:
    def __init__(self, api_client: kubernetes.client.ApiClient, service: str = SERVICE_NAME):
        self.batch_api_instance = kubernetes.client.BatchV1Api(api_client)
        self.core_api_instance = kubernetes.client.CoreV1Api(api_client)
        self.service = service

    def is_pod_present(self, namespace: str, client_id: str, action_id: str):
        label_selector = KubernetesDispatcher.get_label_selector(client_id, action_id)
        pods: V1PodList = self.core_api_instance.list_namespaced_pod(namespace, label_selector=label_selector)
        return bool(pods.items)

    def is_job_present(self, namespace: str, client_id: str, action_id: str):
        label_selector = KubernetesDispatcher.get_label_selector(client_id, action_id)
        pods: V1PodList = self.batch_api_instance.list_namespaced_job(namespace, label_selector=label_selector)
        return bool(pods.items)

    def wait_for_pod_exists(self, namespace: str, client_id: str, action_id: str):
        while not self.is_pod_present(namespace, client_id, action_id):
            sleep(1)

    def wait_for_pod_not_exists(self, namespace: str, client_id: str, action_id: str):
        while self.is_pod_present(namespace, client_id, action_id):
            sleep(1)

    def wait_for_job_exists(self, namespace: str, client_id: str, action_id: str):
        while not self.is_job_present(namespace, client_id, action_id):
            sleep(1)

    def wait_for_job_not_exists(self, namespace: str, client_id: str, action_id: str):
        while self.is_job_present(namespace, client_id, action_id):
            sleep(1)
