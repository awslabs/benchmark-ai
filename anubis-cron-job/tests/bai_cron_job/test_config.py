from bai_cron_job.config import get_config


def test_env_var_config():
    argv = []
    env_vars = {"KAFKA_BOOTSTRAP_SERVERS": "a,b,c", "PRODUCER_TOPIC": "topic", "BENCHMARK_EVENT": '{"key": "value"}'}
    config = get_config(argv, env_vars)
    assert config.kafka_bootstrap_servers == ["a", "b", "c"]
    assert config.producer_topic == "topic"
    assert config.benchmark_event == {"key": "value"}
