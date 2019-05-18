from bai_kafka_utils.events import DataSet, BenchmarkEvent
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher

# This test can be executed from IDE


# API boundary test - should just not fail starting the job - the job itself can fail
def test_kuberenetes_client(k8s_dispatcher: KubernetesDispatcher, benchmark_event_dummy_payload: BenchmarkEvent):
    data_set = DataSet(src="http://somedata.big", dst="s3://dst", md5=None)
    k8s_dispatcher(data_set, benchmark_event_dummy_payload, "/data/sets/fake")
