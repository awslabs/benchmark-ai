import logging
import pycurl
import tempfile
from enum import IntEnum

from typing import Optional

from benchmarkai_fetcher_job.failures import HttpClientError, HttpServerError
from benchmarkai_fetcher_job.md5sum import validate_md5
from benchmarkai_fetcher_job.s3_utils import S3Object, upload_to_s3


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


def http_to_s3(src: str, dst: str, md5: Optional[str] = None):
    logger.info(f"http to s3: {src} -> {dst}")

    s3dst = S3Object.parse(dst)

    logger.info(f"S3dst {s3dst}")

    with tempfile.TemporaryFile("r+b") as fp:
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
        curl.perform()

        status = curl.getinfo(pycurl.HTTP_CODE)
        family = HTTPFamily.from_status(status)
        if family == HTTPFamily.CLIENT_ERROR:
            raise HttpClientError()
        if family == HTTPFamily.SERVER_ERROR:
            raise HttpServerError()

        logger.info(f"End download {src}")

        if md5:
            fp.seek(0)
            validate_md5(fp, md5)

        fp.seek(0)
        upload_to_s3(fp, s3dst)
