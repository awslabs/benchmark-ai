import logging
from math import ceil

import kubernetes
from kubernetes.client import (
    V1PersistentVolumeClaim,
    V1PersistentVolumeClaimSpec,
    V1ResourceRequirements,
    V1EmptyDirVolumeSource,
    V1PersistentVolumeClaimVolumeSource,
    V1Volume,
    V1VolumeMount,
    V1EnvVar,
    V1PodTemplateSpec,
    V1PodSpec,
    V1ObjectMeta,
    V1Container,
    V1JobSpec,
    V1JobStatus,
    V1Job,
    BatchV1Api,
    CoreV1Api,
    ApiClient,
    Configuration,
)
from typing import Dict, List, Optional

from bai_kafka_utils.events import DataSet, BenchmarkEvent
from bai_kafka_utils.utils import id_generator
from fetcher_dispatcher.args import FetcherJobConfig
from fetcher_dispatcher.data_set_manager import DataSetDispatcher
from preflight.data_set_size import DataSetSizeInfo

X = 16

logger = logging.getLogger(__name__)


def create_kubernetes_api_client(kubeconfig: str) -> ApiClient:
    logger.info("Initializing with KUBECONFIG=%s", kubeconfig)

    if kubeconfig:
        kubernetes.config.load_kube_config(kubeconfig)
    else:
        kubernetes.config.load_incluster_config()

    configuration = Configuration()
    return ApiClient(configuration)


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

    TMP_DIR = "TMP_DIR"

    TMP_MOUNT_PATH = "/var/tmp/"

    TMP_VOLUME = "tmp-volume"

    def __init__(self, service_name: str, kubeconfig: str, zk_ensemble: str, fetcher_job: FetcherJobConfig):
        self.service_name = service_name
        self.zk_ensemble = zk_ensemble
        self.fetcher_job = fetcher_job

        api_client = create_kubernetes_api_client(kubeconfig)

        self.batch_api_instance = BatchV1Api(api_client)
        self.core_api_instance = CoreV1Api(api_client)

    def _get_fetcher_job(
        self, task: DataSet, event: BenchmarkEvent, zk_node_path: str, volume_claim_name: Optional[str]
    ) -> V1Job:

        job_metadata = V1ObjectMeta(
            namespace=self.fetcher_job.namespace, name=self._get_job_name(task), labels=self._get_labels(task, event)
        )

        job_status = V1JobStatus()

        pod_template = self._get_fetcher_pod_template(task, event, zk_node_path, volume_claim_name)
        job_spec = V1JobSpec(ttl_seconds_after_finished=self.fetcher_job.ttl, template=pod_template)

        return V1Job(api_version="batch/v1", kind="Job", spec=job_spec, status=job_status, metadata=job_metadata)

    # TODO Implement some human readable name from DataSet
    def _get_job_name(self, task: DataSet) -> str:
        return "fetcher-" + id_generator()

    def _get_fetcher_pod_template(
        self, task: DataSet, event: BenchmarkEvent, zk_node_path: str, volume_claim_name: Optional[str]
    ) -> V1PodTemplateSpec:
        pod_spec = self._get_fetcher_pod_spec(task, zk_node_path, volume_claim_name)
        return V1PodTemplateSpec(spec=pod_spec, metadata=V1ObjectMeta(labels=self._get_labels(task, event)))

    def _get_fetcher_pod_spec(self, task: DataSet, zk_node_path: str, volume_claim_name: Optional[str]):
        volume = self._get_fetcher_volume(volume_claim_name)
        container = self._get_fetcher_container(task, zk_node_path)

        return V1PodSpec(
            containers=[container],
            volumes=[volume],
            restart_policy=self.fetcher_job.restart_policy,
            node_selector=self.fetcher_job.node_selector,
        )

    def _get_fetcher_volume(self, volume_claim_name: str = None):
        return V1Volume(
            name=KubernetesDispatcher.TMP_VOLUME,
            persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=volume_claim_name)
            if volume_claim_name
            else None,
            empty_dir=None if volume_claim_name else V1EmptyDirVolumeSource(),
        )

    def _get_fetcher_container(self, task: DataSet, zk_node_path: str) -> V1Container:
        job_args = self._get_args(task, zk_node_path)
        env_list = self._get_env()
        return V1Container(
            name=KubernetesDispatcher.FETCHER_CONTAINER_NAME,
            image=self.fetcher_job.image,
            args=job_args,
            env=env_list,
            image_pull_policy=self.fetcher_job.pull_policy,
            volume_mounts=[
                V1VolumeMount(name=KubernetesDispatcher.TMP_VOLUME, mount_path=KubernetesDispatcher.TMP_MOUNT_PATH)
            ],
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

    def _get_env(self) -> List[V1EnvVar]:
        return [
            V1EnvVar(name=KubernetesDispatcher.ZOOKEEPER_ENSEMBLE_HOSTS, value=self.zk_ensemble),
            V1EnvVar(name=KubernetesDispatcher.TMP_DIR, value=KubernetesDispatcher.TMP_MOUNT_PATH),
        ]

    def _get_labels(self, task: DataSet, event: BenchmarkEvent) -> Dict[str, str]:
        return {
            KubernetesDispatcher.ACTION_ID_LABEL: event.action_id,
            KubernetesDispatcher.CLIENT_ID_LABEL: event.client_id,
            KubernetesDispatcher.CREATED_BY_LABEL: self.service_name,
        }

    @staticmethod
    def get_label_selector(service_name: str, client_id: str, action_id: str = None):
        selector = (
            f"{KubernetesDispatcher.CREATED_BY_LABEL}={service_name},"
            + f"{KubernetesDispatcher.CLIENT_ID_LABEL}={client_id}"
        )
        if action_id:
            selector += f",{KubernetesDispatcher.ACTION_ID_LABEL}={action_id}"
        return selector

    def _get_label_selector(self, client_id: str, action_id: str = None):
        return KubernetesDispatcher.get_label_selector(self.service_name, client_id, action_id)

    def dispatch_fetch(self, task: DataSet, size_info: DataSetSizeInfo, event: BenchmarkEvent, zk_node_path: str):
        try:
            volume_claim: str = None

            volume_size = KubernetesDispatcher._get_volume_size(size_info)

            if volume_size >= self.fetcher_job.volume.min_size:
                volume_claim = "pv-" + self._get_job_name(task)
                # Do we need a volume?
                pv_metadata = V1ObjectMeta(
                    namespace=self.fetcher_job.namespace, name=volume_claim, labels=self._get_labels(task, event)
                )

                volume_body = V1PersistentVolumeClaim(
                    metadata=pv_metadata,
                    spec=V1PersistentVolumeClaimSpec(
                        access_modes=["ReadWriteOnce"],
                        storage_class_name=self.fetcher_job.volume.storage_class,
                        resources=V1ResourceRequirements(requests={"storage": f"{volume_size}M"}),
                    ),
                )
                resp = self.core_api_instance.create_namespaced_persistent_volume_claim(
                    self.fetcher_job.namespace, volume_body
                )

            fetcher_job = self._get_fetcher_job(task, event, zk_node_path, volume_claim)

            resp = self.batch_api_instance.create_namespaced_job(self.fetcher_job.namespace, fetcher_job, pretty=True)
            logger.debug("k8s response: %s", resp)
        except Exception:
            logger.exception("Failed to create a kubernetes job")
            raise

    def cancel_all(self, client_id: str, action_id: str = None):
        logger.info(f"Removing jobs {client_id}/{action_id}")
        action_id_label_selector = self._get_label_selector(client_id, action_id)

        jobs_response = self.batch_api_instance.delete_collection_namespaced_job(
            self.fetcher_job.namespace, label_selector=action_id_label_selector
        )
        logger.debug("k8s response: %s", jobs_response)
        pods_response = self.core_api_instance.delete_collection_namespaced_pod(
            self.fetcher_job.namespace, label_selector=action_id_label_selector
        )
        logger.debug("k8s response: %s", pods_response)

    @staticmethod
    def _get_volume_size(size_info: DataSetSizeInfo):
        # Max file + 20% just for any case.
        # Not less than 10% of total size
        # Round to the next X mb. X=16
        MB = 1024 * 1024
        XMB = X * MB
        return X * ceil(max(size_info.max_size * 1.2, size_info.total_size * 0.1) / XMB)
