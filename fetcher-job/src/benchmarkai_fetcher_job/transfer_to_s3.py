import logging
import tempfile

from typing import Optional, TextIO, Callable

from benchmarkai_fetcher_job.failures import InvalidDigestError
from benchmarkai_fetcher_job.http_utils import http_download
from benchmarkai_fetcher_job.md5sum import calculate_md5_and_etag, DigestPair
from benchmarkai_fetcher_job.s3_utils import (
    S3Object,
    upload_to_s3,
    check_s3_for_md5,
    check_s3_for_etag,
    update_s3_hash_tagging,
)

logger = logging.getLogger(__name__)

DownloadCallback = Callable[[TextIO, str], None]


def transfer_to_s3(download: DownloadCallback, src: str, dst: str, md5: Optional[str] = None):
    logger.info(f"transfer to s3: {src} -> {dst}")

    s3dst = S3Object.parse(dst)

    logger.info(f"S3dst {s3dst}")

    if md5 and check_s3_for_md5(s3dst, md5):
        logger.info(f"S3 Object with md5 {md5} found - good enough")
        return

    with tempfile.TemporaryFile("r+b") as fp:
        download(fp, src)

        hash_pair: DigestPair = calculate_md5_and_etag(fp)

        if md5:
            if hash_pair.md5 != md5:
                logger.info(f"Invalid md5 {hash_pair.md5} found")
                raise InvalidDigestError()
            logger.info("Hash validation passed")

        # Now we know the "real" etag - may be we can spare the upload?
        if not check_s3_for_etag(s3dst, hash_pair.s3_etag):
            upload_to_s3(fp, s3dst)
        else:
            logger.info(f"S3 Object with etag {hash_pair.s3_etag} found - good enough")

        # If we are here - hash is either missing or wrong.
        # So let's update it
        update_s3_hash_tagging(s3dst, hash_pair.md5)
