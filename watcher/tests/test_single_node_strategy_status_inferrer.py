import pytest

from kubernetes.client import (
    V1JobStatus,
    V1JobCondition,
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

BACKOFF_LIMIT_EXCEEDED_COND = V1JobCondition(
    reason="BackoffLimitExceeded", type="Failed", status="True", message="Job has reached the specified backoff limit"
)


@pytest.mark.parametrize(
    "failed,succeeded,conditions,expected_status",
    [
        (4, 0, [BACKOFF_LIMIT_EXCEEDED_COND], BenchmarkJobStatus.FAILED),
        (4, None, [BACKOFF_LIMIT_EXCEEDED_COND], BenchmarkJobStatus.FAILED),
        (3, 1, [], BenchmarkJobStatus.SUCCEEDED),
    ],
)
def test_job_status(failed, succeeded, conditions, expected_status):
    job_status = V1JobStatus(succeeded=succeeded, failed=failed, conditions=conditions)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(job_status, pods=[])
    assert inferrer.status() == expected_status


def test_no_pods_scheduled_for_k8s_job_yet():
    k8s_job_status = V1JobStatus(active=1)
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(k8s_job_status, pods=[])
    assert inferrer.status() == BenchmarkJobStatus.NO_POD_SCHEDULED


def test_pod_in_running_phase():
    pod = V1Pod(status=V1PodStatus(phase="Running"))
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[pod])
    assert inferrer.status() == BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS


def test_pod_scaling_nodes():
    condition = V1PodCondition(type="PodScheduled", reason="Unschedulable", status="False")
    status = V1PodStatus(phase="Pending", conditions=[condition])
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[V1Pod(status=status)])
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
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[pod])
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
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[pod])
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
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[pod])
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
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[pod])
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
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[pod])
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
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[pod])
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
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[pod])
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
    inferrer = SingleNodeStrategyKubernetesStatusInferrer(V1JobStatus(active=1), pods=[pod])
    assert inferrer.status() == BenchmarkJobStatus.FAILED_AT_SIDECAR_CONTAINER
