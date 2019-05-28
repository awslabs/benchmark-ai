import logging
import os

from bai_fetcher_job.args import FetcherJobConfig, get_fetcher_job_args
from bai_fetcher_job.fetcher import retrying_fetch
from bai_kafka_utils.utils import LOGGING_FORMAT


def main(argv=None):
    cfg: FetcherJobConfig = get_fetcher_job_args(argv, os.environ)
    logging.basicConfig(level=cfg.logging_level, format=LOGGING_FORMAT)

    retrying_fetch(cfg)


if __name__ == "__main__":
    main()
