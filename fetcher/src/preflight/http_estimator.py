import pycurl

from bai_io_utils.http_utils import http_perform
from bai_kafka_utils.events import DataSetSizeInfo


def http_estimate_size(src) -> DataSetSizeInfo:
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, src)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 60)  # 60s should be enough to send HEAD and get back
    curl.setopt(pycurl.HEADER, 1)
    curl.setopt(pycurl.NOBODY, 1)

    http_perform(curl)

    content_length = curl.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD)

    return DataSetSizeInfo(int(content_length), 1, int(content_length))
