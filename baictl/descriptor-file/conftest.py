import pytest

from transpiler.bai_knowledge import EnvironmentInfo


@pytest.fixture
def bai_environment_info():
    return EnvironmentInfo(
        availability_zones=["us-east-1a", "us-east-1b", "us-east-1c"]
    )
