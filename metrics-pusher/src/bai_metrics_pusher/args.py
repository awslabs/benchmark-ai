import inspect
import os

import configargparse
from bai_metrics_pusher.backends import BACKENDS
from dataclasses import dataclass, field
from typing import Optional, Dict, Callable, List


@dataclass()
class InputValue:
    backend: str
    pod_name: Optional[str]
    pod_namespace: Optional[str]
    backend_args: Dict[str, str]
    fifo_filenames: List[str] = field(default_factory=list)


def get_input(argv, environ: Dict[str, str] = None) -> InputValue:
    if environ is None:
        environ = os.environ
    parser = configargparse.ArgumentParser(auto_env_var_prefix="", prog="bai-metrics-pusher")
    parser.add_argument("--backend", default="stdout", choices=list(BACKENDS.keys()))
    parser.add_argument("--pod-name")
    parser.add_argument("--pod-namespace")

    class SplitEnvironmentVariableValueAction(configargparse.Action):
        def __init__(self, option_strings, dest, **kwargs):
            super(SplitEnvironmentVariableValueAction, self).__init__(option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            splitted_values = []
            for v in values:
                splitted_values.extend(v.split(" "))
            setattr(namespace, self.dest, splitted_values)

    parser.add_argument(
        "--fifo-filenames", nargs="+", default=["/tmp/benchmarkai/fifo"], action=SplitEnvironmentVariableValueAction
    )

    args = parser.parse_args(argv)

    environ = {key.lower(): value for key, value in environ.items()}
    backend_args = create_dict_of_parameter_values_for_callable(
        prefix="backend_arg_", values=environ, method=BACKENDS[args.backend]
    )

    return InputValue(
        backend=args.backend,
        backend_args=backend_args,
        pod_name=args.pod_name,
        pod_namespace=args.pod_namespace,
        fifo_filenames=args.fifo_filenames,
    )


def create_dict_of_parameter_values_for_callable(prefix: str, values: Dict[str, str], method: Callable):
    """
    Creates a dict with the parameters that can be accepted by the signature of :param(method).

    The returned dictionary can be used to invoke :param(method) by doing dictionary unpacking

    Example:

        def foo(arg1: str, arg2: int):
            pass

        args = create_dict_of_parameter_values_for_callable(
                   prefix="prefix_",
                   values={"prefix_arg1": "string",
                           "prefix_arg2": 42},
                   method=foo)
        foo(**args)

    If :param(values) contains

    :param prefix: A prefix to limit the items considered when inspecting the keys in :param(values).
    :param values: The values to inspect for parameters that can be passed to :param(method)
    :param method: The method to inspect
    :return:
    :raises: AssertionError when :param(method) does not have all its parameters annotated
    """
    signature = inspect.signature(method)

    for key, string_value in values.items():
        if key.startswith(prefix):
            argname = key[len(prefix) :]
            if argname not in signature.parameters:
                raise KeyError("Parameter `%s` does not exist in: %s" % (argname, method))

    args = {}
    for argname, parameter in signature.parameters.items():
        parameter_type = parameter.annotation
        assert parameter_type != inspect.Parameter.empty, "Parameter `%s` has no type annotation in: %s" % (
            argname,
            method,
        )

        key = prefix + argname
        if key not in values:
            raise ValueError(
                "Parameter `%s` of `%s` is missing from the specified values. Prefix: `%s`. Specified keys: %s"
                % (argname, method, prefix, set(values.keys()))
            )

        string_value = values[key]

        if parameter_type == List[str]:
            value = string_value.split(",")
        elif parameter_type == List[int]:
            value = map(int, string_value.split(","))
            value = list(value)
        else:
            value = parameter_type(string_value)

        args[argname] = value
    return args
