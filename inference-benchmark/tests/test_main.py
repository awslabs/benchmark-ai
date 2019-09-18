import os

import pytest
from pytest import fixture

from bai_inference_benchmark.__main__ import main
from bai_inference_benchmark.inference_benchmark import InferenceBenchmarkFailedError

BENCHMARK_NAMESPACE = "default"
BENCHMARK_POD_SPEC = "/path/to/client.yaml"
SERVER_POD_SPEC = "/path/to/server.yaml"


@fixture
def good_inference_benchmark(mocker):
    return mocker.patch("bai_inference_benchmark.__main__.InferenceBenchmark", autospec=True).return_value


@fixture
def bad_inference_benchmark(mocker):
    instance = mocker.patch("bai_inference_benchmark.__main__.InferenceBenchmark", autospec=True).return_value
    instance.execute.side_effect = InferenceBenchmarkFailedError("There was an error")
    return instance


@fixture
def env(mocker):
    return mocker.patch.dict(
        os.environ,
        {
            "BENCHMARK_NAMESPACE": BENCHMARK_NAMESPACE,
            "BENCHMARK_POD_SPEC": BENCHMARK_POD_SPEC,
            "SERVER_POD_SPEC": SERVER_POD_SPEC,
        },
    )


def test_main_calls_execute(good_inference_benchmark, env):
    main()
    good_inference_benchmark.execute.assert_called_once()


def test_main_exits_on_error(bad_inference_benchmark, env):
    with pytest.raises(SystemExit):
        main()
