from pathlib import Path
from bai_inference_benchmark.args import InferenceBenchmarkConfig, get_inference_benchmark_config

BENCHMARK_NAMESPACE = "default"
BENCHMARK_POD_SPEC = Path("/path/to/client.yaml")
SERVER_POD_SPEC = Path("/path/to/server.yaml")

ALL_ARGS = (
    f" --benchmark-namespace={BENCHMARK_NAMESPACE}"
    f" --benchmark-pod-spec={BENCHMARK_POD_SPEC} "
    f" --server-pod-spec={SERVER_POD_SPEC}"
)


def test_get_inference_benchmark_config():
    expected_cfg = InferenceBenchmarkConfig(
        benchmark_namespace=BENCHMARK_NAMESPACE, benchmark_pod_spec=BENCHMARK_POD_SPEC, server_pod_spec=SERVER_POD_SPEC
    )
    cfg = get_inference_benchmark_config(ALL_ARGS)
    assert cfg == expected_cfg


def test_dont_fail_unrecognized():
    get_inference_benchmark_config(ALL_ARGS + " -foo")
