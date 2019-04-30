import os
import random
import pytest
import toml

from pytest_regressions.file_regression import FileRegressionFixture
from transpiler.bai_knowledge import create_job_yaml_spec
from executor.args import create_transpiler_config
from bai_kafka_utils.events import DataSet

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
                     config_args,
                     file_regression: FileRegressionFixture):
    random_object = random.Random()
    random_object.seed(1)

    descriptor_data = toml.load(str(shared_datadir / filename))
    fetched_data_sources = generate_fetched_data_sources(descriptor_data)
    transpiler_config = create_transpiler_config(config_args)

    yaml_spec, _ = create_job_yaml_spec(descriptor_data,
                                        transpiler_config,
                                        fetched_data_sources,
                                        extra_bai_config_args=dict(random_object=random_object))

    basename = os.path.splitext(filename)[0] + "-k8s-object"
    file_regression.check(yaml_spec, basename=basename, extension=".yaml")


def generate_fetched_data_sources(descriptor_data) -> List[DataSet]:
    data_sources = descriptor_data.get('data', {}).get('sources', [])
    if data_sources:
        return [DataSet(src=source['src'], md5='md5', dst=PULLER_S3_URI)
                for source in data_sources]
    else:
        return []
