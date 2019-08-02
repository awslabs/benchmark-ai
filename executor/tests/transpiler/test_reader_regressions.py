import random

import pytest
import toml
from bai_kafka_utils.events import DataSet, FetchedType, FileSystemObject
from pytest_regressions.file_regression import FileRegressionFixture
from typing import List

from executor.args import create_executor_config
from transpiler.bai_knowledge import create_job_yaml_spec

ANUBIS_SCRIPTS = [
    FileSystemObject(dst="s3://script-exchange/anubis/scripts1.tar"),
    FileSystemObject(dst="s3://script-exchange/anubis/scripts2.tar"),
]

PULLER_S3_URI = "s3://puller-data/object-name/dir"
JOB_ID = "benchmark-JOB-ID"


@pytest.mark.parametrize(
    ["descriptor_filename", "expected_yaml", "scripts"],
    [
        ("hello-world.toml", "hello-world", []),
        ("training.toml", "training", []),
        # None should be handled properly as well
        ("training.toml", "training", None),
        ("training.toml", "training-with-script", ANUBIS_SCRIPTS),
        ("horovod.toml", "horovod", []),
        ("horovod.toml", "horovod-with-script", ANUBIS_SCRIPTS),
        ("cronjob.toml", "cronjob", []),
    ],
)
def test_regressions(
    descriptor_filename,
    expected_yaml,
    shared_datadir,
    config_args,
    config_env,
    file_regression: FileRegressionFixture,
    benchmark_event,
    scripts,
):
    random_object = random.Random()
    random_object.seed(1)

    descriptor_data = toml.load(str(shared_datadir / descriptor_filename))
    fetched_data_sources = generate_fetched_data_sources(descriptor_data)
    transpiler_config = create_executor_config(config_args, config_env)

    yaml_spec = create_job_yaml_spec(
        descriptor_data,
        transpiler_config,
        fetched_data_sources,
        scripts,
        JOB_ID,
        extra_bai_config_args=dict(random_object=random_object),
        event=benchmark_event,
    )
    file_regression.check(yaml_spec, basename=expected_yaml, extension=".yaml")


def generate_fetched_data_sources(descriptor_data) -> List[DataSet]:
    data_sources = descriptor_data.get("data", {}).get("sources", [])
    if data_sources:
        return [
            DataSet(src=source["src"], md5="md5", dst=PULLER_S3_URI + str(inx), type=FetchedType.DIRECTORY)
            # Fake different destinations
            for inx, source in enumerate(data_sources)
        ]
    else:
        return []
