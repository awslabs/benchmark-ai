from bai_kafka_utils.events import DataSet, BenchmarkEvent
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher

# This test can be executed from IDE


BENCHMARK_EVENT = BenchmarkEvent(
    action_id="ACTION_ID",
    message_id="DONTCARE",
    client_id="CLIENT_ID",
    client_version="DONTCARE",
    client_username="DONTCARE",
    authenticated=False,
    tstamp=42,
    visited=[],
    payload="DONTCARE",
    type="DONTCARE",
)


# API boundary test - should just not fail
def test_kuberenetes_client(k8s_dispatcher: KubernetesDispatcher):
    data_set = DataSet(src="http://somedata.big", dst="s3://dst", md5=None)
    k8s_dispatcher(data_set, BENCHMARK_EVENT, "/data/sets/fake")
