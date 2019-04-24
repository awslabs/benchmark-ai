import pytest

from transpiler.descriptor import Descriptor


@pytest.mark.parametrize('filename', [
    'missing_keys_descriptor.toml',
    'missing_section_descriptor.toml'
])
def test_wrong_descriptor(datadir, filename, descriptor_config):
    with pytest.raises(KeyError):
        Descriptor.from_toml_file(str(datadir/filename), descriptor_config)


@pytest.mark.parametrize('scheduling', [
    '0 0 0 0',
    '* * ? * *',
    'single'
])
def test_invalid_scheduling(descriptor, scheduling):
    descriptor.scheduling = scheduling
    with pytest.raises(ValueError) as e:
        descriptor._validate()
