from typing import List, Optional

from kubernetes.client import V1JobStatus, V1Pod, V1PodStatus

from bai_watcher import service_logger
from bai_watcher.status_inferrers.common import (
    infer_status_from_containers,
    infer_status_from_pod,
)
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

logger = service_logger.getChild(__name__)


class HorovodStrategyKubernetesStatusInferrer:
    """
    Inspects the strategy "horovod" and returns the final status.
    """

    def __init__(self, k8s_job_status: V1JobStatus, pods: List[V1Pod]):
        self.k8s_job_status = k8s_job_status
        self.pods = pods

    def status(self) -> BenchmarkJobStatus:
        for status_callback in [self._infer_status_from_job, self._infer_status_from_pods]:
            status = status_callback()
            inference_phase_name = status_callback.__name__
            logger.debug(f"Status inference phase '{inference_phase_name}' produced status: {status}")
            if status:
                return status

        raise ValueError(
            "Can't determine what is the job status from {} (there is a bug in the code), erroring the watcher".format(
                self.k8s_job_status
            )
        )

    def _infer_status_from_job(self) -> Optional[BenchmarkJobStatus]:
        if self.k8s_job_status.succeeded is not None:
            return BenchmarkJobStatus.SUCCEEDED

    def _infer_status_from_pods(self):
        if len(self.pods) == 0:
            return BenchmarkJobStatus.NO_POD_SCHEDULED

        pod_statuses: List[V1PodStatus] = [pod.status for pod in self.pods]

        # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase
        phases = [status.phase for status in pod_statuses]
        if "Failed" in phases:
            failing_pod = self.pods[phases.index("Failed")]
            return infer_status_from_containers(failing_pod)
        elif "Pending" in phases:
            pending_pod = self.pods[phases.index("Pending")]
            status = infer_status_from_pod(pending_pod)
            if status:
                return status
            else:
                return infer_status_from_containers(pending_pod)
        elif "Unknown" in phases:
            # TODO: What to do?
            pass
        else:
            # No failed, pending or unknown states, so it mut be running
            # TODO: passing pods[0] isn't really correct, but which one should we pass?
            # An option would be to use the _infer_running_where method commented out  below
            return infer_status_from_containers(self.pods[0])

    """
    def _infer_running_where(self, pods: List[V1Pod]):
        statuses = [infer_status_from_containers(p) for p in pods]
        if BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS in statuses:
            return BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS
        elif BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS in statuses:
            return BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS
        else:
            assert False
    """
