import pytest

from bai_common.events import DataSet


# Rather a boundary test for DataSet optional


def test_data_set_optional_fields_just_src():
    json = '{"src":"http://foo.com"}'
    with pytest.warns(None) as record:
        DataSet.from_json(json)
    assert not record.list


def test_data_set_optional_missing_src():
    json = '{"dst":"http://foo.com", "md5":"42"}'
    with pytest.raises(KeyError):
        DataSet.from_json(json)
