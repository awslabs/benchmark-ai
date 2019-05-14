import logging
import pycurl
from enum import IntEnum
from typing import TextIO

from benchmarkai_fetcher_job.failures import CurlError, HttpClientError, HttpServerError

logger = logging.getLogger(__name__)


class HTTPFamily(IntEnum):
    INFORMATIONAL = 100
    SUCCESS = 200
    REDIRECT = 300
    CLIENT_ERROR = 400
    SERVER_ERROR = 500

    @classmethod
    def from_status(cls, status_code: int):
        return HTTPFamily(status_code - status_code % 100)


def _progress(download_t, download_d, upload_t, upload_d):
    logger.info(f"{download_d} out of {download_t}")


def http_download(fp: TextIO, src: str):
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
