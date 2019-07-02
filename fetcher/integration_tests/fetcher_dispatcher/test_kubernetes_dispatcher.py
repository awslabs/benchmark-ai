import pytest

from bai_kafka_utils.events import DataSet, BenchmarkEvent
from fetcher_dispatcher.args import FetcherJobConfig
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher

# This test can be executed from IDE


# API boundary test - should just not fail starting the job - the job itself can fail
from fetcher_dispatcher.kubernetes_tests_client import KubernetesTestUtilsClient
from preflight.data_set_size import DataSetSizeInfo


S3_DST = "s3://dst"
SOMEDATA_BIG = "http://somedata.big"
SOMEDATA_BIG_WITH_DELAY = "http://somedata.big?delay=120"

BIG_FILE_SIZE = 64 * 1024 * 1024
SMALL_FILE_SIZE = 1024

BIG_SIZE = DataSetSizeInfo(BIG_FILE_SIZE, 1, BIG_FILE_SIZE)
SMALL_SIZE = DataSetSizeInfo(SMALL_FILE_SIZE, 1, SMALL_FILE_SIZE)


@pytest.mark.parametrize("size_info", [BIG_SIZE, SMALL_SIZE], ids=["big", "small"])
def test_kubernetes_client(
    k8s_dispatcher: KubernetesDispatcher,
    benchmark_event_dummy_payload: BenchmarkEvent,
    k8s_test_client: KubernetesTestUtilsClient,
    fetcher_job_config: FetcherJobConfig,
    size_info: DataSetSizeInfo,
):
    data_set = DataSet(src=SOMEDATA_BIG, dst=S3_DST, md5=None)

    k8s_dispatcher.dispatch_fetch(data_set, size_info, benchmark_event_dummy_payload, "/data/sets/fake")

    k8s_test_client.wait_for_pod_exists(
        fetcher_job_config.namespace, benchmark_event_dummy_payload.client_id, benchmark_event_dummy_payload.action_id
    )


# API boundary test - should just not fail
def test_kubernetes_cancel(
    k8s_dispatcher: KubernetesDispatcher,
    benchmark_event_dummy_payload: BenchmarkEvent,
    k8s_test_client: KubernetesTestUtilsClient,
    fetcher_job_config: FetcherJobConfig,
):
    data_set = DataSet(src=SOMEDATA_BIG_WITH_DELAY, dst=S3_DST, md5=None)
    k8s_dispatcher.dispatch_fetch(data_set, benchmark_event_dummy_payload, "/data/sets/fake")

    k8s_test_client.wait_for_job_exists(
        fetcher_job_config.namespace, benchmark_event_dummy_payload.client_id, benchmark_event_dummy_payload.action_id
    )
    k8s_test_client.wait_for_pod_exists(
        fetcher_job_config.namespace, benchmark_event_dummy_payload.client_id, benchmark_event_dummy_payload.action_id
    )

    k8s_dispatcher.cancel_all(benchmark_event_dummy_payload.client_id, benchmark_event_dummy_payload.action_id)

    k8s_test_client.wait_for_pod_not_exists(
        fetcher_job_config.namespace, benchmark_event_dummy_payload.client_id, benchmark_event_dummy_payload.action_id
    )
    k8s_test_client.wait_for_job_not_exists(
        fetcher_job_config.namespace, benchmark_event_dummy_payload.client_id, benchmark_event_dummy_payload.action_id
    )


# API boundary test - should just not fail
def test_kubernetes_cancel_after_ttl(
    k8s_dispatcher: KubernetesDispatcher,
    benchmark_event_dummy_payload: BenchmarkEvent,
    k8s_test_client: KubernetesTestUtilsClient,
    fetcher_job_config: FetcherJobConfig,
):
    # No dispatch - should not throw
    k8s_dispatcher.cancel_all(benchmark_event_dummy_payload.client_id, benchmark_event_dummy_payload.action_id)
