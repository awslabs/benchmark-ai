import logging
import pycurl
import tempfile
from enum import IntEnum

from typing import Optional

from benchmarkai_fetcher_job.failures import HttpClientError, HttpServerError, CurlError
from benchmarkai_fetcher_job.md5sum import calculate_md5_and_etag, DigestPair
from benchmarkai_fetcher_job.s3_utils import (
    S3Object,
    upload_to_s3,
    check_s3_for_md5,
    check_s3_for_etag,
    update_s3_hash_tagging,
)


class HTTPFamily(IntEnum):
    INFORMATIONAL = 100
    SUCCESS = 200
    REDIRECT = 300
    CLIENT_ERROR = 400
    SERVER_ERROR = 500

    @classmethod
    def from_status(cls, status_code: int):
        return HTTPFamily(status_code - status_code % 100)


logger = logging.getLogger(__name__)


def _progress(download_t, download_d, upload_t, upload_d):
    logger.info(f"{download_d} out of {download_t}")


class InvalidDigestError(object):
    pass


def http_to_s3(src: str, dst: str, md5: Optional[str] = None):
    logger.info(f"http to s3: {src} -> {dst}")

    s3dst = S3Object.parse(dst)

    logger.info(f"S3dst {s3dst}")

    if md5 and check_s3_for_md5(s3dst, md5):
        logger.info(f"S3 Object with md5 {md5} found - good enough")
        return

    with tempfile.TemporaryFile("r+b") as fp:
        _download(fp, src)

        hash_pair: DigestPair = calculate_md5_and_etag(fp)

        if md5:
            if hash_pair.md5 != md5:
                logger.info(f"Invalid md5 {hash_pair.md5} found")
                raise InvalidDigestError()
            logger.info("Hash validation passed")

        # Now we know the "real" etag - may be we can spare the upload?
        if not check_s3_for_etag(s3dst, hash_pair.s3_etag):
            upload_to_s3(fp, s3dst)
            return
        logger.info(f"S3 Object with etag {hash_pair.s3_etag} found - good enough")

        # If we are here - hash is either missing or wrong.
        # So let's update it
        update_s3_hash_tagging(s3dst, hash_pair.md5)


def _download(fp, src):
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, src)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)
    curl.setopt(pycurl.NOSIGNAL, 1)
    curl.setopt(pycurl.NOPROGRESS, 0)
    curl.setopt(pycurl.PROGRESSFUNCTION, _progress)
    curl.setopt(pycurl.WRITEDATA, fp)
    logger.info(f"Start download {src}")
    try:
        curl.perform()
    except pycurl.error as e:
        raise CurlError(e)

    status = curl.getinfo(pycurl.HTTP_CODE)
    family = HTTPFamily.from_status(status)
    if family == HTTPFamily.CLIENT_ERROR:
        raise HttpClientError()
    if family == HTTPFamily.SERVER_ERROR:
        raise HttpServerError()
    logger.info(f"End download {src}")
