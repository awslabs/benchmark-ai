#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from __future__ import annotations

from pathlib import Path
from typing import Callable

import kubernetes
from kubernetes.client import V1Job, V1JobStatus, V1PodList, BatchV1Api, CoreV1Api

from bai_watcher import service_logger
from bai_watcher.job_watcher import JobWatcher
from bai_watcher.status_inferrers.single_node import SingleNodeStrategyKubernetesStatusInferrer
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

logger = service_logger.getChild(__name__)

SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS = 10


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
        logger.info("Loading kubeconfig from incluster")
        kubernetes.config.load_incluster_config()


class KubernetesJobWatcher(JobWatcher):
    def __init__(
        self,
        job_id: str,
        callback: Callable[[str, BenchmarkJobStatus], bool],
        *,
        kubernetes_namespace: str,
        kubernetes_client_jobs: BatchV1Api,
        kubernetes_client_pods: CoreV1Api,
    ):
        super().__init__(job_id, callback, SLEEP_TIME_BETWEEN_CHECKING_K8S_STATUS)
        self.kubernetes_namespace = kubernetes_namespace
        self.jobs_client = kubernetes_client_jobs
        self.pod_client = kubernetes_client_pods

    def _get_status(self):
        try:
            k8s_job: V1Job = self.jobs_client.read_namespaced_job_status(self._job_id, self.kubernetes_namespace)
        except kubernetes.client.rest.ApiException as e:
            if e.status == 404:
                return BenchmarkJobStatus.JOB_NOT_FOUND

            logger.exception(
                "Unknown error from Kubernetes, stopping thread that watches job {job_id} with an exception".format(
                    job_id=self._job_id
                )
            )
            raise

        k8s_job_status: V1JobStatus = k8s_job.status
        logger.debug(f"[job-id: {self._job_id}] Kubernetes Job status: {k8s_job_status}")
        logger.debug(f"[job-id: {self._job_id}] Kubernetes Job conditions: {k8s_job_status.conditions}")

        pods: V1PodList = self.pod_client.list_namespaced_pod(
            self.kubernetes_namespace, label_selector=f"job-name={self._job_id}"
        )
        logger.debug(f"[job-id: {self._job_id}] Kubernetes Job pods: {pods}")
        inferrer = SingleNodeStrategyKubernetesStatusInferrer(k8s_job_status, pods.items)
        status = inferrer.status()

        return status
