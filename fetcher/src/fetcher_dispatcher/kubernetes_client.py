import logging
from typing import Dict, List

import kubernetes

from bai_kafka_utils.events import DataSet, BenchmarkEvent
from bai_kafka_utils.utils import id_generator
from fetcher_dispatcher.args import FetcherJobConfig


logger = logging.getLogger(__name__)


class KubernetesDispatcher:
    ACTION_ID_LABEL = "action-id"

    CLIENT_ID_LABEL = "client-id"

    ZK_NODE_PATH_ARG = "--zk-node-path"

    DST_ARG = "--dst"

    SRC_ARG = "--src"

    FETCHER_CONTAINER_NAME = "fetcher"

    ZOOKEEPER_ENSEMBLE_HOSTS = "ZOOKEEPER_ENSEMBLE_HOSTS"

    def __init__(self, kubeconfig: str, zk_ensemble: str, fetcher_job: FetcherJobConfig):
        self.kubeconfig = kubeconfig
        self.zk_ensemble = zk_ensemble
        self.fetcher_job = fetcher_job

        logger.info("Initializing with KUBECONFIG=%s", kubeconfig)

        if self.kubeconfig:
            kubernetes.config.load_kube_config(self.kubeconfig)
        else:
            kubernetes.config.load_incluster_config()

        configuration = kubernetes.client.Configuration()
        self.api_instance = kubernetes.client.BatchV1Api(kubernetes.client.ApiClient(configuration))

    def __dispatch_fetcher(self, task: DataSet, event: BenchmarkEvent, zk_node_path: str):

        fetcher_job = self.get_fetcher_job(task, event, zk_node_path)

        resp = self.api_instance.create_namespaced_job(self.fetcher_job.namespace, fetcher_job, pretty=True)
        logger.debug("k8s response: %s", resp)

    def get_fetcher_job(self, task: DataSet, event: BenchmarkEvent, zk_node_path: str) -> kubernetes.client.V1Job:

        job_metadata = kubernetes.client.V1ObjectMeta(
            namespace=self.fetcher_job.namespace, name=self.get_job_name(task), labels=self.get_labels(task, event)
        )

        job_status = kubernetes.client.V1JobStatus()

        pod_template = self.get_fetcher_pod_template(task, zk_node_path)
        job_spec = kubernetes.client.V1JobSpec(ttl_seconds_after_finished=self.fetcher_job.ttl, template=pod_template)

        return kubernetes.client.V1Job(
            api_version="batch/v1", kind="Job", spec=job_spec, status=job_status, metadata=job_metadata
        )

    # TODO Implement some human readable name from DataSet
    def get_job_name(self, task: DataSet) -> str:
        return "fetcher-" + id_generator()

    def get_fetcher_pod_template(self, task: DataSet, zk_node_path: str) -> kubernetes.client.V1PodTemplateSpec:
        pod_spec = self.get_fetcher_pod_spec(task, zk_node_path)
        return kubernetes.client.V1PodTemplateSpec(spec=pod_spec)

    def get_fetcher_pod_spec(self, task: DataSet, zk_node_path: str):
        container = self.get_fetcher_container(task, zk_node_path)
        return kubernetes.client.V1PodSpec(
            containers=[container],
            restart_policy=self.fetcher_job.restart_policy,
            node_selector=self.fetcher_job.node_selector,
        )

    def get_fetcher_container(self, task: DataSet, zk_node_path: str) -> kubernetes.client.V1Container:
        job_args = self.get_args(task, zk_node_path)
        env_list = self.get_env()
        return kubernetes.client.V1Container(
            name=KubernetesDispatcher.FETCHER_CONTAINER_NAME,
            image=self.fetcher_job.image,
            args=job_args,
            env=env_list,
            image_pull_policy=self.fetcher_job.pull_policy,
        )

    def get_args(self, task: DataSet, zk_node_path: str) -> List[str]:
        return [
            KubernetesDispatcher.SRC_ARG,
            task.src,
            KubernetesDispatcher.DST_ARG,
            task.dst,
            KubernetesDispatcher.ZK_NODE_PATH_ARG,
            zk_node_path,
        ]

    def get_env(self) -> List[kubernetes.client.V1EnvVar]:
        return [kubernetes.client.V1EnvVar(name=KubernetesDispatcher.ZOOKEEPER_ENSEMBLE_HOSTS, value=self.zk_ensemble)]

    def get_labels(self, task: DataSet, event: BenchmarkEvent) -> Dict[str, str]:
        return {
            KubernetesDispatcher.ACTION_ID_LABEL: event.action_id,
            KubernetesDispatcher.CLIENT_ID_LABEL: event.client_id,
        }

    def __call__(self, task: DataSet, event: BenchmarkEvent, zk_node_path: str):
        try:
            self.__dispatch_fetcher(task, event, zk_node_path)
        except Exception:
            logger.exception("Failed to create a kubernetes job")
            raise
