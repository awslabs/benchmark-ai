import logging

from typing import Optional

from benchmarkai_fetcher_job.http_utils import http_download
from benchmarkai_fetcher_job.transfer_to_s3 import transfer_to_s3

logger = logging.getLogger(__name__)


def http_to_s3(src: str, dst: str, md5: Optional[str] = None):
    transfer_to_s3(http_download, src, dst, md5)
