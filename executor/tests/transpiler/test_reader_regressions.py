import random

import pytest
import toml
from bai_kafka_utils.events import DownloadableContent, FetchedType, FileSystemObject
from pytest_regressions.file_regression import FileRegressionFixture
from typing import List

from executor.args import create_executor_config
from transpiler.bai_knowledge import create_job_yaml_spec, create_scheduled_job_yaml_spec, DescriptorError

ANUBIS_SCRIPTS = [
    FileSystemObject(dst="s3://scripts-exchange/anubis/scripts1.tar"),
    FileSystemObject(dst="s3://scripts-exchange/anubis/scripts2.tar"),
]

PULLER_S3_URI = "s3://puller-data/object-name/dir"
PULLER_HTTP_URI = "http://puller-data/object-name/dir"
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
        ("horovod-with-spaces.toml", "horovod", []),
        ("inference.toml", "inference-with-script", ANUBIS_SCRIPTS),
        ("inference.toml", "inference", []),
    ],
)
@pytest.mark.parametrize("parent_action_id", ["parentactionid", None])
def test_single_job_regressions(
    descriptor_filename,
    expected_yaml,
    shared_datadir,
    config_args,
    config_env,
    file_regression: FileRegressionFixture,
    benchmark_event,
    scripts,
    parent_action_id,
):
    random_object = random.Random()
    random_object.seed(1)

    if parent_action_id:
        benchmark_event.parent_action_id = parent_action_id
        expected_yaml = expected_yaml + f"-{parent_action_id}"

    descriptor_data = toml.load(str(shared_datadir / descriptor_filename))
    fetched_data_sources = generate_fetched_data_sources(descriptor_data)
    fetched_models = generate_fetched_models(descriptor_data)
    transpiler_config = create_executor_config(config_args, config_env)
    yaml_spec = create_job_yaml_spec(
        descriptor_data,
        transpiler_config,
        fetched_data_sources,
        fetched_models,
        scripts,
        JOB_ID,
        extra_bai_config_args=dict(random_object=random_object),
        event=benchmark_event,
    )

    file_regression.check(yaml_spec, basename=expected_yaml, extension=".yaml")


@pytest.mark.parametrize(
    ["descriptor_filename", "expected_yaml", "scripts"],
    [
        ("training-with-metrics.toml", "training-with-metrics", None),
        ("training-with-metrics.toml", "training-with-metrics", []),
        ("training-with-metrics.toml", "training-with-metrics-with-script", ANUBIS_SCRIPTS),
        ("horovod-with-metrics.toml", "horovod-with-metrics", None),
        ("horovod-with-metrics.toml", "horovod-with-metrics", []),
        ("horovod-with-metrics.toml", "horovod-with-metrics-with-script", ANUBIS_SCRIPTS),
        ("inference-with-server-metrics.toml", "inference-with-server-metrics", None),
        ("inference-with-server-metrics.toml", "inference-with-server-metrics", []),
        ("inference-with-server-metrics.toml", "inference-with-server-metrics-with-script", ANUBIS_SCRIPTS),
        ("inference-with-server-and-client-metrics.toml", "inference-with-server-and-client-metrics", None),
        ("inference-with-server-and-client-metrics.toml", "inference-with-server-and-client-metrics", []),
        (
            "inference-with-server-and-client-metrics.toml",
            "inference-with-server-and-client-metrics-with-script",
            ANUBIS_SCRIPTS,
        ),
    ],
)
def test_single_job_with_metrics_regressions(
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
    fetched_models = generate_fetched_models(descriptor_data)
    transpiler_config = create_executor_config(config_args, config_env)
    yaml_spec = create_job_yaml_spec(
        descriptor_data,
        transpiler_config,
        fetched_data_sources,
        fetched_models,
        scripts,
        JOB_ID,
        extra_bai_config_args=dict(random_object=random_object),
        event=benchmark_event,
    )

    file_regression.check(yaml_spec, basename=expected_yaml, extension=".yaml")


@pytest.mark.parametrize(["descriptor_filename", "expected_yaml"], [("cronjob.toml", "cronjob")])
def test_scheduled_job_regressions(
    descriptor_filename,
    expected_yaml,
    shared_datadir,
    config_args,
    config_env,
    file_regression: FileRegressionFixture,
    benchmark_event,
):
    random_object = random.Random()
    random_object.seed(1)

    descriptor_data = toml.load(str(shared_datadir / descriptor_filename))
    transpiler_config = create_executor_config(config_args, config_env)

    yaml_spec = create_scheduled_job_yaml_spec(descriptor_data, transpiler_config, JOB_ID, event=benchmark_event)
    file_regression.check(yaml_spec, basename=expected_yaml, extension=".yaml")


def test_raises_with_non_s3_puller_uri(
    shared_datadir, config_args, config_env, file_regression: FileRegressionFixture, benchmark_event
):
    random_object = random.Random()
    random_object.seed(1)

    descriptor_data = toml.load(str(shared_datadir / "training.toml"))
    fetched_data_sources = generate_fetched_data_sources(descriptor_data, http_puller_uri=True)
    transpiler_config = create_executor_config(config_args, config_env)

    with pytest.raises(DescriptorError):
        create_job_yaml_spec(
            descriptor_data,
            transpiler_config,
            fetched_data_sources,
            [],
            [],
            JOB_ID,
            extra_bai_config_args=dict(random_object=random_object),
            event=benchmark_event,
        )


def generate_fetched_data_sources(descriptor_data, http_puller_uri: bool = False) -> List[DownloadableContent]:
    data_sources = descriptor_data.get("data", {}).get("sources", [])
    puller_uri = PULLER_HTTP_URI if http_puller_uri else PULLER_S3_URI
    if data_sources:
        return [
            DownloadableContent(
                src=source["src"], md5="md5", path=source["path"], dst=puller_uri + str(inx), type=FetchedType.DIRECTORY
            )
            # Fake different destinations
            for inx, source in enumerate(data_sources)
        ]
    else:
        return []


def generate_fetched_models(descriptor_data) -> List[DownloadableContent]:
    data_sources = descriptor_data.get("server", {}).get("models", [])
    if data_sources:
        return [
            DownloadableContent(
                src=source["src"],
                md5="md5",
                path=source["path"],
                dst=PULLER_S3_URI + str(inx),
                type=FetchedType.DIRECTORY,
            )
            # Fake different destinations
            for inx, source in enumerate(data_sources)
        ]
    else:
        return []
