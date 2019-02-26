import importlib
import benchmarkai
import os
import pytest


def test_imports_stdout_version_by_default():
    os.environ.pop("BENCHMARK_AI", None)
    importlib.reload(benchmarkai)

    assert benchmarkai.emit == benchmarkai._emit_to_stdout


def test_imports_stdout_version_by_specifying_as_environment_variable():
    os.environ["BENCHMARK_AI"] = "stdout"
    importlib.reload(benchmarkai)

    assert benchmarkai.emit == benchmarkai._emit_to_stdout


def test_unsupported_environment_variable():
    os.environ["BENCHMARK_AI"] = "unsupported-value"
    with pytest.raises(ValueError):
        importlib.reload(benchmarkai)


def test_imports_fifo_version():
    os.environ["BENCHMARK_AI"] = "fifo"
    importlib.reload(benchmarkai)

    assert benchmarkai.emit == benchmarkai._emit_to_fifo
