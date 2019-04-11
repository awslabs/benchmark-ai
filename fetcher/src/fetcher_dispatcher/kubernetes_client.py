import os

import kubernetes

from fetcher_dispatcher.events.data_set import DataSet
from fetcher_dispatcher.utils import id_generator

KUBECONFIG = os.environ.get("KUBECONFIG")
FETCHER_JOB_IMAGE = os.environ.get("FETCHER_JOB_IMAGE")


def dispatch_fetcher(task: DataSet):
    if KUBECONFIG:
        kubernetes.config.load_kube_config(KUBECONFIG)
    else:
        kubernetes.config.load_incluster_config()

    configuration = kubernetes.client.Configuration()
    api_instance = kubernetes.client.BatchV1Api(kubernetes.client.ApiClient(configuration))

    download_job = kubernetes.client.V1Job(api_version="batch/v1", kind="Job")

    download_job.metadata = kubernetes.client.V1ObjectMeta(namespace="default", name="download-" + id_generator())
    download_job.status = kubernetes.client.V1JobStatus()
    # Now we start with the Template...
    template = kubernetes.client.V1PodTemplate()
    template.template = kubernetes.client.V1PodTemplateSpec()

    job_args = [task.src, task.dst]

    container = kubernetes.client.V1Container(name="downloader", image=FETCHER_JOB_IMAGE, args=job_args)
    template.template.spec = kubernetes.client.V1PodSpec(containers=[container], restart_policy='Never',
                                                         node_selector={"node.type": "bai-services"})
    # And finally we can create our V1JobSpec!
    download_job.spec = kubernetes.client.V1JobSpec(ttl_seconds_after_finished=600, template=template.template)

    resp = api_instance.create_namespaced_job("default", download_job, pretty=True)
    print(resp)
