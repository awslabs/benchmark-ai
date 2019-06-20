import collections
import logging
from enum import Enum, auto
from typing import List, Dict, Set, Optional

from kubernetes.client import (
    V1JobStatus,
    V1Pod,
    V1PodStatus,
    V1ContainerStatus,
    V1ContainerState,
    V1ContainerStateTerminated,
    V1ContainerStateWaiting,
    V1ContainerStateRunning,
    V1PodCondition,
)

from bai_watcher.status_inferrers.status import BenchmarkJobStatus


ContainerInfo = collections.namedtuple("ContainerIdAndMessage", ("container_id", "message"))

logger = logging.getLogger(__name__)


class ContainerState(Enum):
    """
    This enum is analogous to the container states listed in
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-states
    """

    FAILED = auto()  # When a container is: terminated & exit_code != 0
    PENDING = auto()
    RUNNING = auto()


def collect_container_states(container_statuses: List[V1ContainerStatus]) -> Dict[ContainerState, Set[ContainerInfo]]:
    """
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-states
    """
    state_to_containers = collections.defaultdict(set)

    # inspect "terminated"
    for status in container_statuses:
        container_state: V1ContainerState = status.state
        if container_state.terminated:
            terminated: V1ContainerStateTerminated = container_state.terminated
            if terminated.exit_code != 0:
                obj = ContainerInfo(status.image_id, f"{terminated.reason} - {terminated.message}")
                state_to_containers[ContainerState.FAILED].add(obj)

    # inspect "waiting"
    for status in container_statuses:
        container_state: V1ContainerState = status.state
        if container_state.waiting:
            waiting: V1ContainerStateWaiting = container_state.waiting
            obj = ContainerInfo(status.image_id, f"{waiting.reason} - {waiting.message}")
            state_to_containers[ContainerState.PENDING].add(obj)

    # inspect "running"
    for status in container_statuses:
        container_state: V1ContainerState = status.state
        if container_state.running:
            running: V1ContainerStateRunning = container_state.running
            obj = ContainerInfo(status.container_id, f"{running.started_at}")
            state_to_containers[ContainerState.RUNNING].add(obj)
    return state_to_containers


class SingleNodeStrategyKubernetesStatusInferrer:
    """
    Inspects the strategy "single-node" and returns the final status.

    This class goes through "multiple phases" in order to arrive the final status:

    # Phase 1 (inspect whole job)

    - If "SUCCEEDED" -> Return early
    - If "NOT ACTIVE" & "FAILED" -> Return early

    # Phase 2 (inspect PODs)
    - If "NO pods found" -> Return early
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

    def __init__(self, k8s_job_status: V1JobStatus, pods: List[V1Pod]):
        self.k8s_job_status = k8s_job_status
        self.pods = pods

    def status(self) -> BenchmarkJobStatus:
        for status_callback in [
            self._infer_status_from_job,
            self._infer_status_from_pod,
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

    def _infer_status_from_pod(self):
        # TODO: Handle multiple PODs for the same Job since Jobs have a retry mechanism
        if len(self.pods) == 0:
            return BenchmarkJobStatus.NO_POD_SCHEDULED
        pod = self.pods[0]
        pod_status: V1PodStatus = pod.status

        # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase
        phase = pod_status.phase
        if phase == "Running":
            return BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS

        if phase == "Pending" and pod_status.conditions:
            # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-conditions
            conditions: List[V1PodCondition] = pod_status.conditions
            # TODO: handle multiple `conditions`
            condition = conditions[0]
            if condition.type == "PodScheduled" and condition.reason == "Unschedulable":
                return BenchmarkJobStatus.PENDING_NODE_SCALING

        # We don't handle the POD phases "Failed" or "Pending" here because we want to inspect each container of the POD

    def _infer_status_from_containers(self):
        pod = self.pods[0]
        pod_status: V1PodStatus = pod.status

        # init containers
        init_containers = collect_container_states(pod_status.init_container_statuses or [])
        if any(len(s) for s in init_containers.values()):
            logger.info(f"[pod: {pod.metadata.name}] Init containers are not done yet: {init_containers}")
        for state, container_infos in init_containers.items():
            if state == ContainerState.PENDING:
                return BenchmarkJobStatus.PENDING_AT_INIT_CONTAINERS
            elif state == ContainerState.RUNNING:
                return BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS
            elif state == ContainerState.FAILED:
                return BenchmarkJobStatus.FAILED_AT_INIT_CONTAINERS
            else:
                assert False

        # benchmark and sidecar containers
        main_containers = collect_container_states(pod_status.container_statuses)
        logger.info(f"[pod: {pod.metadata.name}] Main containers state: {main_containers}")
        for state, container_infos in main_containers.items():
            if state == ContainerState.PENDING:
                for container_info in container_infos:
                    # HACK: It is not great to hardcode the name of the container like this, but Kubernetes does not
                    # have a way to specify which container is a sidecar.
                    if container_info.container_id != "benchmark":
                        return BenchmarkJobStatus.PENDING_AT_SIDECAR_CONTAINER
                    else:
                        return BenchmarkJobStatus.PENDING_AT_BENCHMARK_CONTAINER

            elif state == ContainerState.FAILED:
                for container_info in container_infos:
                    # HACK: It is not great to hardcode the name of the container like this, but Kubernetes does not
                    # have a way to specify which container is a sidecar.
                    if container_info.container_id != "benchmark":
                        return BenchmarkJobStatus.FAILED_AT_SIDECAR_CONTAINER
                    else:
                        return BenchmarkJobStatus.FAILED_AT_BENCHMARK_CONTAINER
            else:
                assert False
