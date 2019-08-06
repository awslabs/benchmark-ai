from enum import auto, Enum


class BenchmarkJobStatus(Enum):
    """
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
    """

    NO_POD_SCHEDULED = auto()
    JOB_DOES_NOT_EXIST = auto()

    FAILED_AT_BENCHMARK_CONTAINER = auto()
    FAILED_AT_SIDECAR_CONTAINER = auto()  # Should never occur, but you never know!
    FAILED_AT_INIT_CONTAINERS = auto()

    PENDING_AT_BENCHMARK_CONTAINER = auto()
    PENDING_AT_SIDECAR_CONTAINER = auto()
    PENDING_AT_INIT_CONTAINERS = auto()
    PENDING_NODE_SCALING = auto()

    RUNNING_AT_INIT_CONTAINERS = auto()
    RUNNING_AT_MAIN_CONTAINERS = auto()

    SUCCEEDED = auto()

    def is_final(self):
        """
        Does this state represent a "final state"
        """
        return self in (
            BenchmarkJobStatus.SUCCEEDED,
            BenchmarkJobStatus.FAILED_AT_INIT_CONTAINERS,
            BenchmarkJobStatus.FAILED_AT_BENCHMARK_CONTAINER,
            BenchmarkJobStatus.FAILED_AT_SIDECAR_CONTAINER,
        )

    def is_running(self):
        return self in (BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS, BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS)
