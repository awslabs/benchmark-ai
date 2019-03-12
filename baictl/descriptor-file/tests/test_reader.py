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
        dr.DescriptorReader(file)


# def test_get_container_args():
#     assert dr.get_container_args({'benchmark_code': 'a.py'}) == 'a.py;'
#     assert dr.get_container_args({'benchmark_code': 'a.py', 'ml_args': '-f'}) == 'a.py -f;'
#
#
# def test_get_data_volumes():
#     data_sources = [{'uri': 's3://data/path1', 'path': '/dest1/'},
#                     {'uri': 's3://data/path2', 'path': '/dest2/'}]
#     expected = {'/dest1/': {'name': 'p0', 'puller_path': '/data/p0'},
#                 '/dest2/': {'name': 'p1', 'puller_path': '/data/p1'}}
#
#     assert dr.get_data_volumes(data_sources) == expected

