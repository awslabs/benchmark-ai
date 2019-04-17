import logging

import kubernetes

from bai_kafka_utils.events import DataSet
from bai_kafka_utils.utils import id_generator

logger = logging.getLogger(__name__)


class KubernetesDispatcher:
    def __init__(self, kubeconfig: str, job_image: str, zk_ensemble: str):
        self.kubeconfig = kubeconfig
        self.job_image = job_image
        self.zk_ensemble = zk_ensemble

        logger.info("Initializing with KUBECONFIG=%s", kubeconfig)

        if self.kubeconfig:
            kubernetes.config.load_kube_config(self.kubeconfig)
        else:
            kubernetes.config.load_incluster_config()

        configuration = kubernetes.client.Configuration()
        self.api_instance = kubernetes.client.BatchV1Api(kubernetes.client.ApiClient(configuration))

    def __dispatch_fetcher(self, task: DataSet, zk_node_path: str):

        download_job = kubernetes.client.V1Job(api_version="batch/v1", kind="Job")

        download_job.metadata = kubernetes.client.V1ObjectMeta(namespace="default", name="download-" + id_generator())
        download_job.status = kubernetes.client.V1JobStatus()
        # Now we start with the Template...
        template = kubernetes.client.V1PodTemplate()
        template.template = kubernetes.client.V1PodTemplateSpec()

        job_args = ["--src", task.src, "--dst", task.dst, "--zk-node-path", zk_node_path]

        env_list = [kubernetes.client.V1EnvVar(name="ZOOKEEPER_ENSEMBLE_HOSTS", value=self.zk_ensemble)]

        container = kubernetes.client.V1Container(name="downloader", image=self.job_image, args=job_args, env=env_list)
        template.template.spec = kubernetes.client.V1PodSpec(containers=[container], restart_policy='Never',
                                                             node_selector={"node.type": "bai-services-network"})
        # And finally we can create our V1JobSpec!
        download_job.spec = kubernetes.client.V1JobSpec(ttl_seconds_after_finished=600, template=template.template)

        resp = self.api_instance.create_namespaced_job("default", download_job, pretty=True)

        logger.info("Job for task %s dispatched", task)
        logger.debug("k8s response: %s", resp)

    def __call__(self, task: DataSet, zk_node_path: str):
        try:
            self.__dispatch_fetcher(task, zk_node_path)
        except Exception:
            logger.exception("Failed to create a kubernetes job")
            raise
