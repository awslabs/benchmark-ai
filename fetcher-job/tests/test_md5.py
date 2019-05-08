import pytest
from pytest import fixture
from typing import TextIO
from unittest.mock import Mock

from benchmarkai_fetcher_job.failures import InvalidDigestException
from benchmarkai_fetcher_job.md5sum import md5sum, validate_md5

FOO_MD5 = "acbd18db4cc2f85cedef654fccc4a4d8"

DATA = b"foo"


@fixture
def mock_file():
    mock_file = Mock(spec=TextIO)
    # Empty binstr to signal EOF
    mock_file.read.side_effect = [DATA, b""]
    return mock_file


def test_md5(mock_file):
    assert FOO_MD5 == md5sum(mock_file)


def test_validate(mock_file):
    validate_md5(mock_file, FOO_MD5)


def test_validate_fail(mock_file):
    with pytest.raises(InvalidDigestException):
        validate_md5(mock_file, "corrupted")
