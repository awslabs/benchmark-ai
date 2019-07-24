import pytest

from bai_kafka_utils.events import DataSet
from bai_kafka_utils.executors.descriptor import DescriptorError

from transpiler.config import BaiDataSource


def test_bai_data_source_invalid_src():
    fetched_source = DataSet(src="whatever/uri", md5="md5", dst="bad://bucket/object")
    with pytest.raises(DescriptorError):
        BaiDataSource(fetched_source, "destination/path")
