import os
from dataclasses import dataclass
from pathlib import Path

from configargparse import ArgParser

from bai_inference_benchmark import NAME


@dataclass
class InferenceBenchmarkConfig:
    benchmark_namespace: str
    benchmark_pod_spec: Path
    server_pod_spec: Path


def get_inference_benchmark_config(args) -> InferenceBenchmarkConfig:
    parser = ArgParser(auto_env_var_prefix="", prog=NAME)
    parser.add("--benchmark-namespace", env_var="BENCHMARK_NAMESPACE", type=str, required=False, default="default")
    parser.add("--benchmark-pod-spec", env_var="BENCHMARK_POD_SPEC", type=Path, required=True)
    parser.add("--server-pod-spec", env_var="SERVER_POD_SPEC", type=Path, required=True)

    parsed_args, _ = parser.parse_known_args(args, env_vars=os.environ)
    return InferenceBenchmarkConfig(
        benchmark_namespace=parsed_args.benchmark_namespace,
        benchmark_pod_spec=parsed_args.benchmark_pod_spec,
        server_pod_spec=parsed_args.server_pod_spec,
    )
