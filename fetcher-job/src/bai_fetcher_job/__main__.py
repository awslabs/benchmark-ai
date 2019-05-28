import os

from bai_fetcher_job.args import FetcherJobConfig, get_fetcher_job_args
from bai_fetcher_job.fetcher import retrying_fetch
from bai_kafka_utils.utils import set_logging_level_and_format


def main(argv=None):
    cfg: FetcherJobConfig = get_fetcher_job_args(argv, os.environ)
    set_logging_level_and_format(cfg.logging_level)

    retrying_fetch(cfg)


if __name__ == "__main__":
    main()
