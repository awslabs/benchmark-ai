import os


def get_test_timeout():
    # Reasonable timeout for all waiting operations
    DEFAULT_TIMEOUT = 30
    return int(os.environ.get("PYTEST_TIMEOUT", DEFAULT_TIMEOUT))
