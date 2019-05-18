from bai_fetcher_job.args import FetcherJobConfig, get_fetcher_job_args, RetryConfig


def test_get_fetcher_job_args():
    cfg: FetcherJobConfig = get_fetcher_job_args(
        "--src=SRC --dst=DST --md5=42 --zk-node-path=/zk/path",
        {
            "LOGGING_LEVEL": "WARN",
            "ZOOKEEPER_ENSEMBLE_HOSTS": "Z1",
            "RETRY_MAX_ATTEMPTS": "11",
            "RETRY_EXP_MAX": "12000",
            "RETRY_EXP_MULTIPLIER": "200",
        },
    )
    assert cfg == FetcherJobConfig(
        src="SRC",
        dst="DST",
        md5="42",
        zk_node_path="/zk/path",
        logging_level="WARN",
        zookeeper_ensemble_hosts="Z1",
        retry=RetryConfig(max_attempts=11, exp_max=12000, exp_multiplier=200),
    )
