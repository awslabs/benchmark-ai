import datetime

import addict
import boto3
import botocore
import pytest
from bai_kafka_utils.events import (
    FetcherBenchmarkEvent,
    FetcherPayload,
    FileSystemObject,
    DownloadableContent,
    ContentSizeInfo,
    FetchedType,
    BenchmarkDoc,
    BenchmarkJob,
)
from bai_kafka_utils.executors.descriptor import BenchmarkDescriptor, DescriptorError
from bai_kafka_utils.executors.execution_callback import ExecutionEngineException, NoResourcesFoundException
from botocore.stub import Stubber
from pytest import fixture
from sagemaker import Session
from sagemaker.estimator import EstimatorBase, Framework
from sm_executor import sm_execution_engine
from sm_executor.args import SageMakerExecutorConfig
from sm_executor.estimator_factory import create_estimator, EstimatorFactory
from sm_executor.sm_execution_engine import SageMakerExecutionEngine
from unittest.mock import create_autospec, PropertyMock

HUGE_DATASET_GB = 100

EXPECTED_HUGE_VOLUME = 110

HUGE_DATASET_SIZE_BYTES = HUGE_DATASET_GB * 1024 ** 3

SCRIPTS = [FileSystemObject(dst="s3://exchange/script.tar")]

ACTION_ID = "ACTION_ID"

CLIENT_ID = "CLIENT_ID"

DATASET_ID = "some_data"

DATASET_S3_URI = "s3://datapull/somedata.zip"

DEFAULT_SM_VOLUME_GB = 30

CREATED_JOB_ID = "MAY_BE_ALSO_ACTION_ID"

TMP_DIR = "/tmp/dir/random"

MOCK_ERROR_RESPONSE = {"Error": {"Message": "Something is wrong"}}


@fixture
def mock_session() -> Session:
    return create_autospec(Session)


@fixture
def prop_train_volume_size():
    return PropertyMock(return_value=DEFAULT_SM_VOLUME_GB)


@fixture
def mock_estimator(prop_train_volume_size) -> EstimatorBase:
    mock = create_autospec(EstimatorBase)
    type(mock).train_volume_size = prop_train_volume_size
    type(mock).latest_training_job = PropertyMock(return_value=addict.Dict(name=CREATED_JOB_ID))
    return mock


@fixture
def mock_estimator_factory(mock_estimator):
    return create_autospec(create_estimator, return_value=mock_estimator)


@fixture
def mock_session_factory(mock_session):
    def _factory():
        return mock_session

    return _factory


MOCKED_REGION = "us-east-1"


def sm_job_description(status: str = "InProgress"):
    return {
        "TrainingJobName": "name",
        "TrainingJobArn": "arn",
        "ModelArtifacts": {"S3ModelArtifacts": "s3stuff"},
        "SecondaryStatus": "secondary",
        "AlgorithmSpecification": {"TrainingInputMode": "mode"},
        "ResourceConfig": {"InstanceType": "", "InstanceCount": 1, "VolumeSizeInGB": 30},
        "StoppingCondition": {},
        "CreationTime": datetime.datetime.now(),
        "TrainingJobStatus": status,
    }


@fixture
def sagemaker_client():
    sagemaker_client = boto3.client("sagemaker", region_name=MOCKED_REGION)
    return sagemaker_client


@fixture
def sm_execution_engine_to_test(
    mock_session_factory, mock_estimator_factory, sagemaker_config: SageMakerExecutorConfig, sagemaker_client
):
    return SageMakerExecutionEngine(
        session_factory=mock_session_factory,
        estimator_factory=mock_estimator_factory,
        config=sagemaker_config,
        sagemaker_client=sagemaker_client,
    )


@fixture
def fetcher_event(descriptor_as_adict) -> FetcherBenchmarkEvent:
    return FetcherBenchmarkEvent(
        action_id=ACTION_ID,
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="CLIENT_VERSION",
        client_username="CLIENT_USER",
        authenticated=False,
        tstamp=42,
        visited=[],
        type="PRODUCER_TOPIC",
        payload=FetcherPayload(
            toml=BenchmarkDoc(contents=descriptor_as_adict.to_dict(), doc="", sha1="SHA"),
            scripts=SCRIPTS,
            datasets=[
                DownloadableContent(
                    src="http://someserver.com/somedata.zip",
                    dst=DATASET_S3_URI,
                    path="/mount/path",
                    id=DATASET_ID,
                    size_info=ContentSizeInfo(total_size=42, file_count=1, max_size=42),
                    type=FetchedType.FILE,
                )
            ],
        ),
    )


@fixture(autouse=True)
def mock_create_source_dir(mocker):
    mock = mocker.patch.object(sm_execution_engine, "ScriptSourceDirectory", autoSpec=True)
    return mock.create


@fixture(autouse=True)
def mock_tmp_dir(mocker):
    mock_tmp_file = mocker.patch.object(sm_execution_engine, "tempfile", autoSpec=True)
    mock_tmp_file.TemporaryDirectory.return_value.__enter__.return_value = TMP_DIR
    return mock_tmp_file


def test_run(
    descriptor: BenchmarkDescriptor,
    sm_execution_engine_to_test: SageMakerExecutionEngine,
    fetcher_event: FetcherBenchmarkEvent,
    mock_create_source_dir,
    mock_estimator: Framework,
):
    job = sm_execution_engine_to_test.run(fetcher_event)

    mock_estimator.fit.assert_called_with({DATASET_ID: DATASET_S3_URI}, job_name=ACTION_ID, wait=False, logs=False)
    mock_create_source_dir.assert_called_with(descriptor, TMP_DIR, SCRIPTS)

    assert job == BenchmarkJob(CREATED_JOB_ID)


@pytest.mark.parametrize(
    ["file_size", "expected_train_volume_size"],
    [(42, DEFAULT_SM_VOLUME_GB), (HUGE_DATASET_SIZE_BYTES, EXPECTED_HUGE_VOLUME)],
)
def test_volume_size(
    file_size: int,
    expected_train_volume_size: int,
    prop_train_volume_size: PropertyMock,
    sm_execution_engine_to_test: SageMakerExecutionEngine,
    fetcher_event: FetcherBenchmarkEvent,
):
    fetcher_event.payload.datasets[0].size_info.max_size = file_size
    fetcher_event.payload.datasets[0].size_info.total_size = file_size

    sm_execution_engine_to_test.run(fetcher_event)
    prop_train_volume_size.assert_called_with(expected_train_volume_size)


def test_merge_metrics(
    sm_execution_engine_to_test: SageMakerExecutionEngine, customparams_descriptor: BenchmarkDescriptor,
):
    metric_data = [
        {"MetricName": "iter", "Value": 51.900001525878906, "Timestamp": "1970-01-19T03:48:31.114000-08:00"},
        {"MetricName": "accuracy", "Value": 51.900001525878906, "Timestamp": "1970-01-19T03:48:31.114000-08:00"},
    ]
    metrics_with_dimensions = [
        {
            "MetricName": "iter",
            "Value": 51.900001525878906,
            "Dimensions": [{"Name": "task_name", "Value": "exampleTask"}, {"Name": "batch_size", "Value": "64"}],
        },
        {
            "MetricName": "accuracy",
            "Value": 51.900001525878906,
            "Dimensions": [{"Name": "task_name", "Value": "exampleTask"}, {"Name": "batch_size", "Value": "64"}],
        },
    ]
    assert sm_execution_engine_to_test.tag_dimensions(customparams_descriptor, metric_data) == metrics_with_dimensions


def test_no_data(
    sagemaker_config: SageMakerExecutorConfig,
    sm_execution_engine_to_test: SageMakerExecutionEngine,
    fetcher_event: FetcherBenchmarkEvent,
    mock_estimator: Framework,
):
    fetcher_event.payload.datasets = []
    sm_execution_engine_to_test.run(fetcher_event)

    mock_estimator.fit.assert_called_with(
        {"src0": sagemaker_config.s3_nodata}, job_name=ACTION_ID, wait=False, logs=False
    )


def test_run_invalid_descriptor(
    sm_execution_engine_to_test: SageMakerExecutionEngine, fetcher_event: FetcherBenchmarkEvent, mock_create_source_dir
):
    fetcher_event.payload.toml.contents["hardware"] = {}
    with pytest.raises(ExecutionEngineException):
        sm_execution_engine_to_test.run(fetcher_event)


def test_run_fail_create_estimator(
    mock_estimator_factory: EstimatorFactory,
    sm_execution_engine_to_test: SageMakerExecutionEngine,
    fetcher_event: FetcherBenchmarkEvent,
):
    mock_estimator_factory.side_effect = DescriptorError("Missing framework")
    with pytest.raises(ExecutionEngineException):
        sm_execution_engine_to_test.run(fetcher_event)


def test_run_fail_from_sagemaker(
    mock_estimator: Framework,
    sm_execution_engine_to_test: SageMakerExecutionEngine,
    fetcher_event: FetcherBenchmarkEvent,
):
    mock_estimator.fit.side_effect = botocore.exceptions.ClientError(MOCK_ERROR_RESPONSE, "start job")
    with pytest.raises(ExecutionEngineException) as err:
        sm_execution_engine_to_test.run(fetcher_event)
    assert str(err.value) == "Benchmark creation failed. SageMaker returned error: Something is wrong"


def test_cancel_raises_not_found(sm_execution_engine_to_test: SageMakerExecutionEngine):
    stub = Stubber(sm_execution_engine_to_test.sagemaker_client)
    stub.add_response(method="describe_training_job", service_response=sm_job_description(status="InProgress"))
    stub.add_client_error(
        "stop_training_job",
        service_error_code="ValidationException",
        service_message="Requested resource not found.",
        expected_params={"TrainingJobName": ACTION_ID},
    )
    stub.activate()

    with pytest.raises(NoResourcesFoundException):
        sm_execution_engine_to_test.cancel(CLIENT_ID, ACTION_ID)


def test_cancel_not_called_on_non_in_progress_status(sm_execution_engine_to_test: SageMakerExecutionEngine):
    stub = Stubber(sm_execution_engine_to_test.sagemaker_client)
    stub.add_response(method="describe_training_job", service_response=sm_job_description(status="Failed"))
    stub.add_client_error(
        "stop_training_job",
        service_error_code="ValidationException",
        service_message="The job status is Failed",
        expected_params={"TrainingJobName": ACTION_ID},
    )
    stub.activate()

    try:
        sm_execution_engine_to_test.cancel(CLIENT_ID, ACTION_ID)
    except Exception as err:
        pytest.fail("stop training got called")
        raise err


def test_cancel_raises(sm_execution_engine_to_test: SageMakerExecutionEngine):
    stub = Stubber(sm_execution_engine_to_test.sagemaker_client)
    stub.add_response(method="describe_training_job", service_response=sm_job_description(status="InProgress"))
    stub.add_client_error(
        "stop_training_job",
        service_error_code="SomeRandomError",
        service_message="Some random error has occured",
        expected_params={"TrainingJobName": ACTION_ID},
    )
    stub.activate()

    with pytest.raises(ExecutionEngineException):
        sm_execution_engine_to_test.cancel(CLIENT_ID, ACTION_ID)
