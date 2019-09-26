import pytest

from kubernetes.client import (
    V1JobStatus,
    V1Pod,
    V1PodStatus,
    V1PodCondition,
    V1ContainerStatus,
    V1ContainerState,
    V1ContainerStateWaiting,
    V1ContainerStateRunning,
    V1ObjectMeta,
    V1ContainerStateTerminated,
)

from bai_watcher.kubernetes_job_watcher import SingleNodeStrategyKubernetesStatusInferrer
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

CONTAINER_STATE_WAITING = V1ContainerStateWaiting(reason=".", message="...")
CONTAINER_STATE_TERMINATED_AND_FAILED = V1ContainerStateTerminated(exit_code=1)
CONTAINER_STATE_TERMINATED_AND_SUCCEEDED = V1ContainerStateTerminated(exit_code=0)

JOB_BACKOFF_LIMIT = 5


@pytest.mark.parametrize("backoff_limit", [-1, 0])
def test_raises_backoff_limit_le_zero(backoff_limit):
    job_status = V1JobStatus(succeeded=0, failed=0)
    with pytest.raises(ValueError):
        SingleNodeStrategyKubernetesStatusInferrer(job_status, pods=[], backoff_limit=backoff_limit)


@pytest.mark.parametrize(
    "failed,succeeded,backoff_limit,expected_status",
    [
        (4, 0, 4, BenchmarkJobStatus.FAILED),
        (5, 0, 4, BenchmarkJobStatus.FAILED),
        (4, None, 4, BenchmarkJobStatus.FAILED),
        (5, None, 4, BenchmarkJobStatus.FAILED),
        (3, 1, 4, BenchmarkJobStatus.SUCCEEDED),
    ],
)
def test_job_status(failed, succeeded, backoff_limit, expected_status):
    job_status = V1JobStatus(succeeded=succeeded, failed=failed)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(job_status, pods=[], backoff_limit=backoff_limit)
    assert inferrer.status() == expected_status


def test_no_pods_scheduled_for_k8s_job_yet():
    k8s_job_status = V1JobStatus(active=1)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(k8s_job_status, pods=[], backoff_limit=JOB_BACKOFF_LIMIT)
    assert inferrer.status() == BenchmarkJobStatus.NO_POD_SCHEDULED


def test_pod_in_running_phase():
    pod = V1Pod(status=V1PodStatus(phase="Running"))
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[pod], backoff_limit=JOB_BACKOFF_LIMIT
    )
    assert inferrer.status() == BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS


def test_pod_scaling_nodes():
    condition = V1PodCondition(type="PodScheduled", reason="Unschedulable", status="False")
    status = V1PodStatus(phase="Pending", conditions=[condition])
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[V1Pod(status=status)], backoff_limit=JOB_BACKOFF_LIMIT
    )
    assert inferrer.status() == BenchmarkJobStatus.PENDING_NODE_SCALING


def test_init_containers_waiting():
    container_state = V1ContainerState(waiting=CONTAINER_STATE_WAITING)
    status = V1PodStatus(
        phase="Pending",
        init_container_statuses=[
            V1ContainerStatus(
                image="benchmarkai/data-puller",
                name="data-puller",
                image_id="",
                ready=False,
                restart_count=0,
                state=container_state,
            )
        ],
    )

    pod = V1Pod(metadata=V1ObjectMeta(name="pod-name"), status=status)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[pod], backoff_limit=JOB_BACKOFF_LIMIT
    )
    assert inferrer.status() == BenchmarkJobStatus.PENDING_AT_INIT_CONTAINERS


def test_init_containers_running():
    container_state = V1ContainerState(running=V1ContainerStateRunning())
    status = V1PodStatus(
        phase="Pending",
        init_container_statuses=[
            V1ContainerStatus(
                image="benchmarkai/data-puller",
                name="data-puller",
                image_id="",
                ready=True,
                restart_count=0,
                state=container_state,
            )
        ],
    )

    pod = V1Pod(metadata=V1ObjectMeta(name="pod-name"), status=status)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[pod], backoff_limit=JOB_BACKOFF_LIMIT
    )
    assert inferrer.status() == BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS


def test_init_containers_failed():
    container_state = V1ContainerState(terminated=V1ContainerStateTerminated(exit_code=1))
    status = V1PodStatus(
        phase="Pending",
        init_container_statuses=[
            V1ContainerStatus(
                image="benchmarkai/data-puller",
                name="data-puller",
                image_id="",
                ready=True,
                restart_count=0,
                state=container_state,
            )
        ],
    )

    pod = V1Pod(metadata=V1ObjectMeta(name="pod-name"), status=status)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[pod], backoff_limit=JOB_BACKOFF_LIMIT
    )
    assert inferrer.status() == BenchmarkJobStatus.FAILED_AT_INIT_CONTAINERS


def test_waiting_for_sidecar_container():
    status = V1PodStatus(
        phase="Pending",
        container_statuses=[
            V1ContainerStatus(
                image="benchmarkai/hello-world",
                name="benchmark",
                image_id="",
                ready=True,
                restart_count=0,
                state=V1ContainerState(running=V1ContainerStateRunning()),
            ),
            V1ContainerStatus(
                image="benchmarkai/metrics-pusher",
                name="sidecar",
                image_id="",
                ready=False,
                restart_count=0,
                state=V1ContainerState(waiting=CONTAINER_STATE_WAITING),
            ),
        ],
    )

    pod = V1Pod(metadata=V1ObjectMeta(name="pod-name"), status=status)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[pod], backoff_limit=JOB_BACKOFF_LIMIT
    )
    assert inferrer.status() == BenchmarkJobStatus.PENDING_AT_SIDECAR_CONTAINER


def test_waiting_for_benchmark_container():
    status = V1PodStatus(
        phase="Pending",
        container_statuses=[
            V1ContainerStatus(
                image="benchmarkai/hello-world",
                name="benchmark",
                image_id="",
                ready=False,
                restart_count=0,
                state=V1ContainerState(waiting=CONTAINER_STATE_WAITING),
            ),
            V1ContainerStatus(
                image="benchmarkai/metrics-pusher",
                name="sidecar",
                image_id="",
                ready=True,
                restart_count=0,
                state=V1ContainerState(running=V1ContainerStateRunning()),
            ),
        ],
    )

    pod = V1Pod(metadata=V1ObjectMeta(name="pod-name"), status=status)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[pod], backoff_limit=JOB_BACKOFF_LIMIT
    )
    assert inferrer.status() == BenchmarkJobStatus.PENDING_AT_BENCHMARK_CONTAINER


def test_failed_at_benchmark_container_but_sidecar_still_running():
    status = V1PodStatus(
        phase="Running",
        container_statuses=[
            V1ContainerStatus(
                image="benchmarkai/hello-world",
                name="benchmark",
                image_id="",
                ready=False,
                restart_count=0,
                state=V1ContainerState(terminated=CONTAINER_STATE_TERMINATED_AND_FAILED),
            ),
            V1ContainerStatus(
                image="benchmarkai/metrics-pusher",
                name="sidecar",
                image_id="",
                ready=True,
                restart_count=0,
                state=V1ContainerState(running=V1ContainerStateRunning()),
            ),
        ],
    )

    pod = V1Pod(metadata=V1ObjectMeta(name="pod-name"), status=status)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[pod], backoff_limit=JOB_BACKOFF_LIMIT
    )
    # TODO: Not sure if this is the status we want
    assert inferrer.status() == BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS


def test_failed_at_benchmark_container_and_pod_terminated():
    status = V1PodStatus(
        phase="Failed",
        container_statuses=[
            V1ContainerStatus(
                image="benchmarkai/hello-world",
                name="benchmark",
                image_id="",
                ready=True,
                restart_count=0,
                state=V1ContainerState(terminated=CONTAINER_STATE_TERMINATED_AND_FAILED),
            ),
            V1ContainerStatus(
                image="benchmarkai/metrics-pusher",
                name="sidecar",
                image_id="",
                ready=True,
                restart_count=0,
                state=V1ContainerState(terminated=CONTAINER_STATE_TERMINATED_AND_SUCCEEDED),
            ),
        ],
    )

    pod = V1Pod(metadata=V1ObjectMeta(name="pod-name"), status=status)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[pod], backoff_limit=JOB_BACKOFF_LIMIT
    )
    assert inferrer.status() == BenchmarkJobStatus.FAILED_AT_BENCHMARK_CONTAINER


def test_failed_at_sidecar_container_and_pod_terminated():
    status = V1PodStatus(
        phase="Failed",
        container_statuses=[
            V1ContainerStatus(
                image="benchmarkai/hello-world",
                name="benchmark",
                image_id="",
                ready=True,
                restart_count=0,
                state=V1ContainerState(terminated=CONTAINER_STATE_TERMINATED_AND_SUCCEEDED),
            ),
            V1ContainerStatus(
                image="benchmarkai/metrics-pusher",
                name="sidecar",
                image_id="",
                ready=True,
                restart_count=0,
                state=V1ContainerState(terminated=CONTAINER_STATE_TERMINATED_AND_FAILED),
            ),
        ],
    )

    pod = V1Pod(metadata=V1ObjectMeta(name="pod-name"), status=status)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(
        V1JobStatus(active=1), pods=[pod], backoff_limit=JOB_BACKOFF_LIMIT
    )
    assert inferrer.status() == BenchmarkJobStatus.FAILED_AT_SIDECAR_CONTAINER
