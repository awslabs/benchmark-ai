import pytest


@pytest.fixture(scope="module")
def bff_endpoint(pytestconfig):
    import os

    bff_env = os.environ.get("BFF_ENDPOINT", None)
    return pytestconfig.getoption("--bff-endpoint") or bff_env


def pytest_addoption(parser):
    parser.addoption("--bff-endpoint")
