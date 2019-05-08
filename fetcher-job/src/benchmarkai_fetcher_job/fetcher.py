import logging
from urllib.parse import urlparse

from retrying import retry

from benchmarkai_fetcher_job.args import FetcherJobConfig
from benchmarkai_fetcher_job.failures import RetryableError, UnRetryableError
from benchmarkai_fetcher_job.http_to_s3 import http_to_s3
from benchmarkai_fetcher_job.s3_to_s3 import s3_to_s3
from benchmarkai_fetcher_job.states import FetcherResult, FetcherStatus
from benchmarkai_fetcher_job.zk_client import update_zk_node

# Current version doesn't stream - we create temporary files.
SUCCESS_MESSAGE = "Success"

logger = logging.getLogger(__name__)


def is_retryable(exc: Exception):
    return isinstance(exc, RetryableError)


def retrying_fetch(cfg: FetcherJobConfig):
    @retry(
        retry_on_exception=is_retryable,
        wait_exponential_multiplier=cfg.retry.exp_multiplier,
        wait_exponential_max=cfg.retry.exp_max,
        stop_max_attempt_number=cfg.retry.max_attempts,
    )
    def _retry_fetch(cfg):
        _fetch(cfg)

    try:
        _retry_fetch(cfg)
    except (RetryableError, UnRetryableError) as ex:
        logger.exception("Predicted error. Unretryable or out of attempts")
        if cfg.zk_node_path:
            _update_zk_node(cfg, FetcherStatus.FAILED, str(ex))
        return
    except Exception:
        logger.exception("Something evil happened. Crash the job. May be lucky next time")
        raise

    _update_zk_node(cfg, FetcherStatus.DONE, SUCCESS_MESSAGE)


def _update_zk_node(cfg: FetcherJobConfig, status: FetcherStatus, msg: str):
    if cfg.zk_node_path:
        update_zk_node(cfg.zk_node_path, cfg.zookeeper_ensemble_hosts, FetcherResult(status, msg))


def _fetch(cfg: FetcherJobConfig):
    print(f"Fetch job = {cfg}\n")

    src_scheme = urlparse(cfg.src)
    if src_scheme.scheme == "http" or src_scheme.scheme == "https":
        http_to_s3(cfg.src, cfg.dst)
    elif src_scheme.scheme == "s3":
        s3_to_s3(cfg.src, cfg.dst)
