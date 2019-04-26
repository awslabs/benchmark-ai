import os
import random
import pytest
import toml

from pytest_regressions.file_regression import FileRegressionFixture
from transpiler.__main__ import create_yaml_spec


@pytest.mark.parametrize("filename", [
    "hello-world.toml",
    "training.toml",
    "horovod.toml",
    "cronjob.toml",
])
def test_regressions(filename,
                     shared_datadir,
                     descriptor_config,
                     bai_config,
                     file_regression: FileRegressionFixture,
                     bai_environment_info):
    random_object = random.Random()
    random_object.seed(1)

    descriptor_data = toml.load(str(shared_datadir / filename))
    yaml_spec = create_yaml_spec(descriptor_data,
                                 descriptor_config,
                                 bai_config,
                                 bai_environment_info,
                                 extra_bai_config_args=dict(random_object=random_object))

    basename = os.path.splitext(filename)[0] + "-k8s-object"
    file_regression.check(yaml_spec, basename=basename, extension=".yaml")
