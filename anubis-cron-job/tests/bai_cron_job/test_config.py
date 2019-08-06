from bai_cron_job.config import get_args


def test_env_var_config():
    argv = []
    env_vars = {"KAFKA_BOOTSTRAP_SERVERS": "a,b,c", "PRODUCER_TOPIC": "topic", "BENCHMARK_EVENT": '{"key": "value"}'}
    args = get_args(argv, env_vars)
    assert args.kafka_bootstrap_servers == ["a", "b", "c"]
    assert args.producer_topic == "topic"
    assert args.benchmark_event == {"key": "value"}
