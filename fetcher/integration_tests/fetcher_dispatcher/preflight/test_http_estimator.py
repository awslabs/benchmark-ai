from preflight.data_set_size import DataSetSizeInfo
from preflight.http_estimator import http_estimate_size

BIG_FILE = "http://dataserver:8080/big-file"

# Test environment has a file with a line "HUGE FILE", which is 9 bytes.
HUGE_SIZE = 9


def test_http_estimator():
    assert http_estimate_size(BIG_FILE) == DataSetSizeInfo(HUGE_SIZE, 1, HUGE_SIZE)
