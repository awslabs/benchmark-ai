from enum import Enum


class BenchmarkJobStatus(Enum):
    """
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
    """

    NO_POD_SCHEDULED = "NO_POD_SCHEDULED"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"

    FAILED_AT_BENCHMARK_CONTAINER = "FAILED_AT_BENCHMARK_CONTAINER"
    FAILED_AT_SIDECAR_CONTAINER = "FAILED_AT_SIDECAR_CONTAINER"  # Should never occur, but you never know!
    FAILED_AT_INIT_CONTAINERS = "FAILED_AT_INIT_CONTAINERS"

    PENDING_AT_BENCHMARK_CONTAINER = "PENDING_AT_BENCHMARK_CONTAINER"
    PENDING_AT_SIDECAR_CONTAINER = "PENDING_AT_SIDECAR_CONTAINER"
    PENDING_AT_INIT_CONTAINERS = "PENDING_AT_INIT_CONTAINERS"
    PENDING_NODE_SCALING = "PENDING_NODE_SCALING"

    RUNNING_AT_INIT_CONTAINERS = "RUNNING_AT_INIT_CONTAINERS"
    RUNNING_AT_MAIN_CONTAINERS = "RUNNING_AT_MAIN_CONTAINERS"

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

    def is_final(self):
        """
        Does this state represent a "final state"
        """
        return self in (
            BenchmarkJobStatus.SUCCEEDED,
            BenchmarkJobStatus.FAILED_AT_INIT_CONTAINERS,
            BenchmarkJobStatus.FAILED_AT_BENCHMARK_CONTAINER,
            BenchmarkJobStatus.FAILED_AT_SIDECAR_CONTAINER,
            BenchmarkJobStatus.JOB_NOT_FOUND,
            BenchmarkJobStatus.FAILED,
        )

    def is_running(self):
        return self in (BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS, BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS)
