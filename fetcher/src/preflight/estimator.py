from urllib.parse import urlparse

from retrying import retry

from bai_io_utils.failures import RetryableError
from bai_kafka_utils.events import DataSetSizeInfo
from preflight.http_estimator import http_estimate_size
from preflight.s3_estimator import s3_estimate_size

MAX_ATTEMPTS = 3

WAIT_EXPONENTIAL_MAX_MS = 3000

WAIT_EXPONENTIAL_MULTIPLIER_MS = 500


class UnknownSchemeException(Exception):
    pass


@retry(
    retry_on_exception=lambda exc: isinstance(exc, RetryableError),
    wait_exponential_multiplier=WAIT_EXPONENTIAL_MULTIPLIER_MS,
    wait_exponential_max=WAIT_EXPONENTIAL_MAX_MS,
    stop_max_attempt_number=MAX_ATTEMPTS,
)
def estimate_fetch_size(src: str) -> DataSetSizeInfo:
    parsed = urlparse(src)
    if parsed.scheme == "http" or parsed.scheme == "https":
        return http_estimate_size(src)
    if parsed.scheme == "s3":
        return s3_estimate_size(src)
    raise UnknownSchemeException(f"Unknown scheme '{parsed.scheme}' in '{src}'")
