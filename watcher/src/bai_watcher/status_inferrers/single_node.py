from typing import List, Optional
from kubernetes.client import V1JobStatus, V1Pod
from bai_watcher import service_logger
from bai_watcher.status_inferrers.common import (
    infer_status_from_pod,
    infer_status_from_containers,
)
from bai_watcher.status_inferrers.status import BenchmarkJobStatus


logger = service_logger.getChild(__name__)


class SingleNodeStrategyKubernetesStatusInferrer:
    """
    Inspects the strategy "single-node" and returns the final status.

    This class goes through "multiple phases" in order to arrive the final status:

    # Phase 1 (inspect whole job)

    - If "SUCCEEDED" -> Return early
    - If "NOT ACTIVE" & "FAILED" -> Return early

    # Phase 2 (inspect PODs)
    - If "NO pods found" -> Return early
    - If POD triggered a node scaling -> Return early
    - If "RUNNING" -> Return early

    # Phase 3 (inspect containers)
    - Scan init containers:
        - If container.failed -> Return early
        - If container.running -> Return early
        - If container.pending -> Return early

    - Scan main containers:
        - If container.failed:
            - Inspect which container failed (benchmark or sidecar) -> Return early
        - If container.pending -> Return early
        - If container.running -> continue loop
    """

    """
    Name of the container inside the POD that is running a benchmark.

    Must be in sync with what the name that the Executor gives to the benchmark container.

    HACK: It is not great to hardcode the name of the container like this, but Kubernetes does not
          have a way to specify which container is a sidecar.
    """

    def __init__(self, k8s_job_status: V1JobStatus, pods: List[V1Pod]):
        self.k8s_job_status = k8s_job_status
        self.pods = pods

    def status(self) -> BenchmarkJobStatus:
        for status_callback in [
            self._infer_status_from_job,
            self._infer_status_from_pods,
            self._infer_status_from_containers,
        ]:
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
        # TODO: Handle multiple PODs for the same Job since Jobs have a retry mechanism
        if len(self.pods) == 0:
            return BenchmarkJobStatus.NO_POD_SCHEDULED
        pod = self.pods[0]

        return infer_status_from_pod(pod)

    def _infer_status_from_containers(self):
        pod = self.pods[0]

        return infer_status_from_containers(pod)
