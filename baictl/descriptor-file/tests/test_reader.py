import pytest
import os
import re

import descriptor_reader as dr


DESCRIPTOR_MISSING_KEY = os.path.join(os.path.dirname(__file__), 'missing_keys_descriptor.toml')
DESCRIPTOR_MISSING_SECTION = os.path.join(os.path.dirname(__file__), 'missing_section_descriptor.toml')
DESCRIPTOR_NO_OPTIONAL_FIELDS = os.path.join(os.path.dirname(__file__), 'no_optional_fields_descriptor.toml')

KUBERNETES_MAX_ID_LEN = 63
KUBERNETES_ID_REGEX = '[a-z0-9]([-a-z0-9]*[a-z0-9])?'


@pytest.mark.parametrize('file', [
    DESCRIPTOR_MISSING_KEY,
    DESCRIPTOR_MISSING_SECTION
])
def test_wrong_descriptor(file):
    with pytest.raises(KeyError):
        dr.Descriptor.from_toml_file(file)


def test_optional_fields():
    descriptor = dr.Descriptor.from_toml_file(DESCRIPTOR_NO_OPTIONAL_FIELDS)
    assert descriptor.extended_shm is False
    assert descriptor.privileged is False


@pytest.fixture()
def bai_config():
    def _get_bai_config(toml_file):
        descriptor = dr.Descriptor.from_toml_file(toml_file)
        return dr.BaiConfig(descriptor)

    return _get_bai_config


def test_bai_config_job_id(bai_config):
    config = bai_config(DESCRIPTOR_NO_OPTIONAL_FIELDS)
    assert len(config.job_id) <= KUBERNETES_MAX_ID_LEN
    assert re.fullmatch(KUBERNETES_ID_REGEX, config.job_id)


def test_bai_config__get_container_args(bai_config):
    config = bai_config(DESCRIPTOR_NO_OPTIONAL_FIELDS)
    assert config.container_args == 'benchmark code ;'


def test_bai_config_get_data_volumes(bai_config):
    config = bai_config(DESCRIPTOR_NO_OPTIONAL_FIELDS)
    data_sources = [{'uri': 's3://data/path1', 'path': '/dest1/'},
                    {'uri': 's3://data/path2', 'path': '/dest2/'}]
    expected = {'/dest1/': {'name': 'p0', 'puller_path': '/data/p0'},
                '/dest2/': {'name': 'p1', 'puller_path': '/data/p1'}}

    assert config._get_data_volumes(data_sources) == expected

