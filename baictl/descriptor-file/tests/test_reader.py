import pytest
import os

import descriptor_reader as dr


DESCRIPTOR_MISSING_KEY = os.path.join(os.path.dirname(__file__), 'missing_keys_descriptor.toml')
DESCRIPTOR_MISSING_SECTION = os.path.join(os.path.dirname(__file__), 'missing_section_descriptor.toml')


@pytest.mark.parametrize('file', [
    DESCRIPTOR_MISSING_KEY,
    DESCRIPTOR_MISSING_SECTION
])
def test_wrong_descriptor(file):
    with pytest.raises(KeyError):
        dr.read_descriptor(file)


def test_get_container_args():
    assert dr.get_container_args({'benchmark_code': 'a.py'}) == 'a.py;'
    assert dr.get_container_args({'benchmark_code': 'a.py', 'ml_args': '-f'}) == 'a.py -f;'
    assert dr.get_container_args({'benchmark_code': 'a.py', 'download_cmd': 'data.sh'}) == 'data.sh; a.py;'


def test_fill_init_containers():
    template = "{fetcher_args}"
    assert dr.fill_init_containers([{'download': 'a'}, {'download': 'b'}], template) == 'a; b;'
    assert dr.fill_init_containers([{'download': 'a', 'action': 'b'}, {'download': 'c'}], template) == 'a; b; c;'
