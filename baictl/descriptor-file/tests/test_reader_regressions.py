import os
import random
import pytest
import toml

from pytest_regressions.file_regression import FileRegressionFixture
from transpiler.__main__ import create_yaml_spec
from transpiler.config import FetchedDataSource

from typing import List


PULLER_S3_URI = "s3://puller-data/object-name/dir"


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
    fetched_data_sources = generate_fetched_data_sources(descriptor_data)

    yaml_spec = create_yaml_spec(descriptor_data,
                                 descriptor_config,
                                 bai_config,
                                 fetched_data_sources,
                                 bai_environment_info,
                                 extra_bai_config_args=dict(random_object=random_object))

    basename = os.path.splitext(filename)[0] + "-k8s-object"
    file_regression.check(yaml_spec, basename=basename, extension=".yaml")


def generate_fetched_data_sources(descriptor_data) -> List[FetchedDataSource]:
    data_sources = descriptor_data.get('data', {}).get('sources', [])
    if data_sources:
        return [FetchedDataSource(uri=source['uri'], md5='md5', dst=PULLER_S3_URI)
                for source in data_sources]
    else:
        return []
