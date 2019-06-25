import logging

import kubernetes
from typing import Dict, List

from bai_kafka_utils.events import DataSet, BenchmarkEvent
from bai_kafka_utils.utils import id_generator
from fetcher_dispatcher import SERVICE_NAME
from fetcher_dispatcher.args import FetcherJobConfig
from fetcher_dispatcher.data_set_manager import DataSetDispatcher

logger = logging.getLogger(__name__)


def create_kubernetes_api_client(kubeconfig: str) -> kubernetes.client.ApiClient:
    logger.info("Initializing with KUBECONFIG=%s", kubeconfig)

    if kubeconfig:
        kubernetes.config.load_kube_config(kubeconfig)
    else:
        kubernetes.config.load_incluster_config()

    configuration = kubernetes.client.Configuration()
    return kubernetes.client.ApiClient(configuration)


class KubernetesDispatcher(DataSetDispatcher):
    ACTION_ID_LABEL = "action-id"

    CLIENT_ID_LABEL = "client-id"

    CREATED_BY_LABEL = "created-by"

    ZK_NODE_PATH_ARG = "--zk-node-path"

    DST_ARG = "--dst"

    SRC_ARG = "--src"

    MD5_ARG = "--md5"

    FETCHER_CONTAINER_NAME = "fetcher"

    ZOOKEEPER_ENSEMBLE_HOSTS = "ZOOKEEPER_ENSEMBLE_HOSTS"

    def __init__(self, service_name: str, kubeconfig: str, zk_ensemble: str, fetcher_job: FetcherJobConfig):
        self.service_name = service_name
        self.zk_ensemble = zk_ensemble
        self.fetcher_job = fetcher_job

        api_client = create_kubernetes_api_client(kubeconfig)

        self.batch_api_instance = kubernetes.client.BatchV1Api(api_client)
        self.core_api_instance = kubernetes.client.CoreV1Api(api_client)

    def _get_fetcher_job(self, task: DataSet, event: BenchmarkEvent, zk_node_path: str) -> kubernetes.client.V1Job:

        job_metadata = kubernetes.client.V1ObjectMeta(
            namespace=self.fetcher_job.namespace, name=self._get_job_name(task), labels=self._get_labels(task, event)
        )

        job_status = kubernetes.client.V1JobStatus()

        pod_template = self._get_fetcher_pod_template(task, event, zk_node_path)
        job_spec = kubernetes.client.V1JobSpec(ttl_seconds_after_finished=self.fetcher_job.ttl, template=pod_template)

        return kubernetes.client.V1Job(
            api_version="batch/v1", kind="Job", spec=job_spec, status=job_status, metadata=job_metadata
        )

    # TODO Implement some human readable name from DataSet
    def _get_job_name(self, task: DataSet) -> str:
        return "fetcher-" + id_generator()

    def _get_fetcher_pod_template(
        self, task: DataSet, event: BenchmarkEvent, zk_node_path: str
    ) -> kubernetes.client.V1PodTemplateSpec:
        pod_spec = self._get_fetcher_pod_spec(task, zk_node_path)
        return kubernetes.client.V1PodTemplateSpec(
            spec=pod_spec, metadata=kubernetes.client.V1ObjectMeta(labels=self._get_labels(task, event))
        )

    def _get_fetcher_pod_spec(self, task: DataSet, zk_node_path: str):
        container = self._get_fetcher_container(task, zk_node_path)
        return kubernetes.client.V1PodSpec(
            containers=[container],
            restart_policy=self.fetcher_job.restart_policy,
            node_selector=self.fetcher_job.node_selector,
        )

    def _get_fetcher_container(self, task: DataSet, zk_node_path: str) -> kubernetes.client.V1Container:
        job_args = self._get_args(task, zk_node_path)
        env_list = self._get_env()
        return kubernetes.client.V1Container(
            name=KubernetesDispatcher.FETCHER_CONTAINER_NAME,
            image=self.fetcher_job.image,
            args=job_args,
            env=env_list,
            image_pull_policy=self.fetcher_job.pull_policy,
        )

    def _get_args(self, task: DataSet, zk_node_path: str) -> List[str]:
        return [
            KubernetesDispatcher.SRC_ARG,
            task.src,
            KubernetesDispatcher.DST_ARG,
            task.dst,
            KubernetesDispatcher.ZK_NODE_PATH_ARG,
            zk_node_path,
            KubernetesDispatcher.MD5_ARG,
            task.md5,
        ]

    def _get_env(self) -> List[kubernetes.client.V1EnvVar]:
        return [kubernetes.client.V1EnvVar(name=KubernetesDispatcher.ZOOKEEPER_ENSEMBLE_HOSTS, value=self.zk_ensemble)]

    def _get_labels(self, task: DataSet, event: BenchmarkEvent) -> Dict[str, str]:
        return {
            KubernetesDispatcher.ACTION_ID_LABEL: event.action_id,
            KubernetesDispatcher.CLIENT_ID_LABEL: event.client_id,
            KubernetesDispatcher.CREATED_BY_LABEL: self.service_name,
        }

    def get_label_selector(self, client_id: str, action_id: str = None):
        selector = (
            f"{KubernetesDispatcher.CREATED_BY_LABEL}={self.service_name},"
            + f"{KubernetesDispatcher.CLIENT_ID_LABEL}={client_id}"
        )
        if action_id:
            selector += f",{KubernetesDispatcher.ACTION_ID_LABEL}={action_id}"
        return selector

    def dispatch_fetch(self, task: DataSet, event: BenchmarkEvent, zk_node_path: str):
        try:
            fetcher_job = self._get_fetcher_job(task, event, zk_node_path)

            resp = self.batch_api_instance.create_namespaced_job(self.fetcher_job.namespace, fetcher_job, pretty=True)
            logger.debug("k8s response: %s", resp)
        except Exception:
            logger.exception("Failed to create a kubernetes job")
            raise

    def cancel_all(self, client_id: str, action_id: str = None):
        logger.info(f"Removing jobs {client_id}/{action_id}")
        action_id_label_selector = self.get_label_selector(client_id, action_id)

        jobs_response = self.batch_api_instance.delete_collection_namespaced_job(
            self.fetcher_job.namespace, label_selector=action_id_label_selector
        )
        logger.debug("k8s response: %s", jobs_response)
        pods_response = self.core_api_instance.delete_collection_namespaced_pod(
            self.fetcher_job.namespace, label_selector=action_id_label_selector
        )
        logger.debug("k8s response: %s", pods_response)
        pass
