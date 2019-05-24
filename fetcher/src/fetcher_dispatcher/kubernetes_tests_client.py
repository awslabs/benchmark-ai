from time import sleep

import kubernetes
from kubernetes.client import V1PodList

from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher


class KubernetesTestUtilsClient:
    def __init__(self, api_client: kubernetes.client.ApiClient):
        self.batch_api_instance = kubernetes.client.BatchV1Api(api_client)
        self.core_api_instance = kubernetes.client.CoreV1Api(api_client)

    def is_pod_present(self, namespace: str, client_id: str, action_id: str):
        label_selector = (
            f"{KubernetesDispatcher.ACTION_ID_LABEL}={action_id},{KubernetesDispatcher.CLIENT_ID_LABEL}={client_id}"
        )
        pods: V1PodList = self.core_api_instance.list_namespaced_pod(namespace, label_selector=label_selector)
        return bool(pods.items)

    def wait_for_pod_exists(self, namespace: str, client_id: str, action_id: str):
        while not self.is_pod_present(namespace, client_id, action_id):
            sleep(1)

    def wait_for_pod_not_exists(self, namespace: str, client_id: str, action_id: str):
        while self.is_pod_present(namespace, client_id, action_id):
            sleep(1)
