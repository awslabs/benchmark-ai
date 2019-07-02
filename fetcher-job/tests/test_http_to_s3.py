from unittest.mock import patch

import bai_fetcher_job
from bai_fetcher_job.http_to_s3 import http_to_s3

TEMP_DIR = "/var/tmp"

MD5 = "42"

DST = "s3://mybucket/data.zip"

SRC = "http://someserver/data.zip"


@patch.object(bai_fetcher_job.http_to_s3, "http_download")
@patch.object(bai_fetcher_job.http_to_s3, "transfer_to_s3")
def test_http_to_s3(mock_transfer_to_s3, mock_http_download):
    http_to_s3(SRC, DST, MD5, TEMP_DIR)
    mock_transfer_to_s3.assert_called_with(mock_http_download, SRC, DST, MD5, TEMP_DIR)
