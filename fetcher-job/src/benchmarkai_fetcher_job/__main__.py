import logging
import os

from benchmarkai_fetcher_job.args import FetcherJobConfig, get_fetcher_job_args
from benchmarkai_fetcher_job.fetcher import retrying_fetch


def main(argv=None):
    cfg: FetcherJobConfig = get_fetcher_job_args(argv, os.environ)
    logging.basicConfig(level=cfg.logging_level)

    retrying_fetch(cfg)


if __name__ == "__main__":
    main()
