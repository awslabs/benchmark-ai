import pytest


@pytest.fixture(scope="module")
def bff_endpoint(pytestconfig):
    import os

    return pytestconfig.getoption("--bff-endpoint", default=os.environ.get("BFF_ENDPOINT", None))


def pytest_addoption(parser):
    parser.addoption("--bff-endpoint")
