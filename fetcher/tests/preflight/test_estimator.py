import pytest
from pytest import fixture

import preflight
from preflight.estimator import estimate_fetch_size, UnknownSchemeException

HTTP_SRC = "http://something"

S3_SRC = "s3://something"

FTP_SRC = "ftp://something"


@fixture
def mock_http_estimator(mocker):
    return mocker.patch.object(preflight.estimator, "http_estimate_size")


@fixture
def mock_s3_estimator(mocker):
    return mocker.patch.object(preflight.estimator, "s3_estimate_size")


def test_estimate_fetch_size_http(mock_http_estimator, mock_s3_estimator):
    estimate_fetch_size(HTTP_SRC)
    mock_http_estimator.assert_called_once_with(HTTP_SRC)
    mock_s3_estimator.assert_not_called()


def test_estimate_fetch_size_s3(mock_http_estimator, mock_s3_estimator):
    estimate_fetch_size(S3_SRC)
    mock_s3_estimator.assert_called_once_with(S3_SRC)
    mock_http_estimator.assert_not_called()


def test_estimate_fetch_size_ftp(mock_http_estimator, mock_s3_estimator):
    with pytest.raises(UnknownSchemeException):
        estimate_fetch_size(FTP_SRC)
