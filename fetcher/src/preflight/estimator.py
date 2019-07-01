from urllib.parse import urlparse

from preflight.data_set_size import DataSetSizeInfo
from preflight.http_estimator import http_estimate_size
from preflight.s3_estimator import s3_estimate_size


class UnknownSchemeException(Exception):
    pass


def estimate_fetch_size(src: str) -> DataSetSizeInfo:
    parsed = urlparse(src)
    if parsed.scheme == "http" or parsed.scheme == "https":
        return http_estimate_size(src)
    if parsed.scheme == "s3":
        return s3_estimate_size(src)
    raise UnknownSchemeException("Unknown scheme")
