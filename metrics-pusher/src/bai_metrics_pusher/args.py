import inspect
import os
import typing

import configargparse
from bai_metrics_pusher.backends import BACKENDS
from dataclasses import dataclass
from typing import Optional, Dict, Callable


@dataclass()
class InputValue:
    backend: str
    pod_name: Optional[str]
    pod_namespace: Optional[str]
    backend_args: Dict[str, str]


def get_input(argv, environ=None) -> InputValue:
    if environ is None:
        environ = os.environ
    parser = configargparse.ArgumentParser(auto_env_var_prefix="", prog="bai-metrics-pusher")
    parser.add_argument("--backend", default="stdout", choices=list(BACKENDS.keys()))
    parser.add_argument("--pod-name")
    parser.add_argument("--pod-namespace")

    args = parser.parse_args(argv)

    # TODO: These args should be parsed by the parser => https://github.com/MXNetEdge/benchmark-ai/issues/65
    backend_args = _get_backend_args(environ, backend_class=BACKENDS[args.backend])

    return InputValue(
        backend=args.backend, backend_args=backend_args, pod_name=args.pod_name, pod_namespace=args.pod_namespace
    )


def _get_backend_args(environ, backend_class):
    return create_dict_of_parameter_values_for_callable(prefix="BACKEND_ARG_", values=environ, method=backend_class)


def create_dict_of_parameter_values_for_callable(prefix: str, values: Dict[str, str], method: Callable):
    signature = inspect.signature(method)

    args = {}
    for key, string_value in values.items():
        if key.startswith(prefix):
            argname = key[len(prefix) :].lower()
            try:
                parameter = signature.parameters[argname]
            except KeyError:
                raise KeyError("Parameter `%s` does not exist in: %s" % (argname, method))

            parameter_type = parameter.annotation
            assert parameter_type != inspect.Parameter.empty, "Parameter `%s` has no type annotation in: %s" % (
                argname,
                method,
            )

            if parameter_type == typing.List[str]:
                value = string_value.split(",")
            elif parameter_type == typing.List[int]:
                value = map(int, string_value.split(","))
                value = list(value)
            else:
                value = parameter_type(string_value)
            args[argname] = value
    return args
