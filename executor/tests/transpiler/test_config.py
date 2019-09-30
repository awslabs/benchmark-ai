import pytest

from bai_kafka_utils.events import DownloadableContent
from bai_kafka_utils.executors.descriptor import DescriptorError

from transpiler.config import BaiDataSource


def test_bai_data_source_invalid_src():
    fetched_source = DownloadableContent(src="whatever/uri", md5="md5", dst="bad://bucket/object")
    with pytest.raises(DescriptorError):
        BaiDataSource(fetched_source, "destination/path")
