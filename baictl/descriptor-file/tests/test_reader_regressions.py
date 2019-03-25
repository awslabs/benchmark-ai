import os
import random

import pytest
from pytest_regressions.file_regression import FileRegressionFixture

from descriptor_reader import Descriptor, create_bai_config


@pytest.mark.parametrize("filename", [
    "hello-world.toml",
    "training.toml",
])
def test_regressions(filename, shared_datadir, file_regression: FileRegressionFixture):
    random_object = random.Random()
    random_object.seed(1)

    descriptor = Descriptor.from_toml_file(str(shared_datadir / filename))
    bai_config = create_bai_config(descriptor, extra_bai_config_args=dict(random_object=random_object))
    basename = os.path.splitext(filename)[0] + "-k8s-object"
    file_regression.check(bai_config.dump_yaml_string(), basename=basename, extension=".yaml")
