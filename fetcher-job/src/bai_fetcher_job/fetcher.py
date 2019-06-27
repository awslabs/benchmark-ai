import logging
from urllib.parse import urlparse

from bai_zk_utils.states import FetcherStatus, FetcherResult, FetchedType
from bai_zk_utils.zk_client import update_zk_node
from retrying import retry

from bai_fetcher_job.args import FetcherJobConfig
from bai_fetcher_job.failures import RetryableError, UnRetryableError
from bai_fetcher_job.http_to_s3 import http_to_s3
from bai_fetcher_job.s3_to_s3 import s3_to_s3

# Current version doesn't stream - we create temporary files.
SUCCESS_MESSAGE = "Success"

logger = logging.getLogger(__name__)


def retrying_fetch(cfg: FetcherJobConfig):
    @retry(
        retry_on_exception=lambda exc: isinstance(exc, RetryableError),
        wait_exponential_multiplier=cfg.retry.exp_multiplier,
        wait_exponential_max=cfg.retry.exp_max,
        stop_max_attempt_number=cfg.retry.max_attempts,
    )
    def _retry_fetch(cfg) -> FetchedType:
        return _fetch(cfg)

    fetched_type = None
    try:
        fetched_type = _retry_fetch(cfg)
    except (RetryableError, UnRetryableError) as ex:
        logger.exception("Download error. Unretryable or out of attempts")
        _update_zk_node(cfg, FetcherResult(status=FetcherStatus.FAILED, message=str(ex)))
        return

    _update_zk_node(cfg, FetcherResult(status=FetcherStatus.DONE, message=SUCCESS_MESSAGE, type=fetched_type))


def _update_zk_node(cfg: FetcherJobConfig, result: FetcherResult):
    if cfg.zk_node_path:
        update_zk_node(cfg.zk_node_path, cfg.zookeeper_ensemble_hosts, result)


def _fetch(cfg: FetcherJobConfig) -> FetchedType:
    logger.info(f"Fetch job = {cfg}\n")

    src_scheme = urlparse(cfg.src)
    if src_scheme.scheme == "http" or src_scheme.scheme == "https":
        http_to_s3(cfg.src, cfg.dst, cfg.md5, cfg.tmp_dir)
        return FetchedType.FILE
    elif src_scheme.scheme == "s3":
        return s3_to_s3(cfg.src, cfg.dst, cfg.md5, cfg.tmp_dir)
