import pytest

from transpiler.descriptor import Descriptor


@pytest.mark.parametrize('filename', [
    'missing_keys_descriptor.toml',
    'missing_section_descriptor.toml'
])
def test_wrong_descriptor(datadir, filename):
    with pytest.raises(KeyError):
        Descriptor.from_toml_file(str(datadir/filename))
