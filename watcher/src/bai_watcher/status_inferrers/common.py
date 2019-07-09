import collections

from enum import Enum, auto
from typing import List, Dict, Set

from kubernetes.client import V1ContainerStatus, V1ContainerState, V1ContainerStateTerminated, V1ContainerStateWaiting, \
    V1ContainerStateRunning


ContainerInfo = collections.namedtuple("ContainerInfo", ("container_name", "message"))
BENCHMARK_CONTAINER_NAME = "benchmark"


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

    for status in container_statuses:
        container_state: V1ContainerState = status.state
        if container_state.terminated:
            terminated: V1ContainerStateTerminated = container_state.terminated
            if terminated.exit_code != 0:
                obj = ContainerInfo(status.name, f"{terminated.reason} - {terminated.message}")
                state_to_containers[ContainerState.FAILED].add(obj)

        if container_state.waiting:
            waiting: V1ContainerStateWaiting = container_state.waiting
            obj = ContainerInfo(status.name, f"{waiting.reason} - {waiting.message}")
            state_to_containers[ContainerState.PENDING].add(obj)

        if container_state.running:
            running: V1ContainerStateRunning = container_state.running
            obj = ContainerInfo(status.name, f"{running.started_at}")
            state_to_containers[ContainerState.RUNNING].add(obj)
    return state_to_containers
