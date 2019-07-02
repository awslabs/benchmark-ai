import pytest
from typing import TextIO
from unittest.mock import create_autospec

from bai_io_utils.md5sum import calculate_md5_and_etag, DigestPair

SMALL_MD5 = "acbd18db4cc2f85cedef654fccc4a4d8"

BIG_MD5 = "3858f62230ac3c915f300c664312c63f"

BIG_ETAG = "0105fcbc9eea8193de8e1834677b6c6b-2"

SMALL_DATA = b"foo"

ADDITIONAL_DATA = b"bar"

CHUNK_SIZE = 2


@pytest.mark.parametrize(
    ["file_reads", "expected_digest_pair"],
    [
        ([SMALL_DATA, b""], DigestPair(SMALL_MD5, SMALL_MD5)),
        ([SMALL_DATA, ADDITIONAL_DATA, b""], DigestPair(BIG_MD5, BIG_ETAG)),
    ],
)
def test_calculate_md5_and_etag_mult_chunks(file_reads, expected_digest_pair):
    mock_file = create_autospec(TextIO)
    mock_file.read.side_effect = file_reads

    assert expected_digest_pair == calculate_md5_and_etag(mock_file, CHUNK_SIZE)
