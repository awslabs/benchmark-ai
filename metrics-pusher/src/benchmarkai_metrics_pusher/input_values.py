import os
import configargparse
from benchmarkai_metrics_pusher.backends import BACKENDS
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass()
class InputValue:
    backend: str
    pod_name: Optional[str]
    pod_namespace: Optional[str]
    backend_args: Dict[str, str]


def get_input(argv) -> InputValue:
    parser = configargparse.ArgumentParser(
        auto_env_var_prefix="", prog="bai-metrics-pusher"
    )
    parser.add_argument("--backend", default="stdout", choices=list(BACKENDS.keys()))
    parser.add_argument("--pod-name")
    parser.add_argument("--pod-namespace")

    args = parser.parse_args(argv)

    # TODO: These args should be parsed by the parser => https://github.com/MXNetEdge/benchmark-ai/issues/65
    backend_args = {}
    for key, value in os.environ.items():
        if key.startswith("BACKEND_ARG_"):
            argname = key.lstrip("BACKEND_ARG_").lower()
            backend_args[argname] = value

    return InputValue(
        backend=args.backend,
        backend_args=backend_args,
        pod_name=args.pod_name,
        pod_namespace=args.pod_namespace,
    )
