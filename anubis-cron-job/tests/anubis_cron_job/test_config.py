import pytest
import os
from anubis_cron_job.config import get_config


@pytest.fixture
def mock_env(mocker):
    mocker.patch.object(
        os,
        "environ",
        {"KAFKA_BOOTSTRAP_SERVERS": "a,b,c", "PRODUCER_TOPIC": "topic", "BENCHMARK_EVENT": '{"key": "value"}'},
    )


def test_env_var_config(mock_env):
    argv = []
    config = get_config(argv, os.environ)
    assert config.kafka_bootstrap_servers == ["a", "b", "c"]
    assert config.producer_topic == "topic"
    assert config.benchmark_event == {"key": "value"}
