import pytest
import os
from anubis_cron_job.config import get_config


@pytest.fixture
def mock_env(mocker):
    env = {
        "KAFKA_BOOTSTRAP_SERVERS": "a,b,c",
        "PRODUCER_TOPIC": "topic",
        "STATUS_TOPIC": "status",
        "BENCHMARK_EVENT": '{"key": "value"}',
    }
    mocker.patch.object(os, "environ", env)


def test_env_var_config(mock_env):
    argv = []
    config = get_config(argv, os.environ)
    assert config.kafka_bootstrap_servers == ["a", "b", "c"]
    assert config.producer_topic == "topic"
    assert config.status_topic == "status"
    assert config.benchmark_event == {"key": "value"}
