import pytest
from transpiler.config import BaiDataSource, FetchedDataSource


def test_bai_data_source_invalid_uri():
    fetched_source = FetchedDataSource(
        uri="whatever/uri",
        md5="md5",
        dst="bad://bucket/object"
    )
    with pytest.raises(ValueError):
        BaiDataSource(fetched_source, "destination/path")
