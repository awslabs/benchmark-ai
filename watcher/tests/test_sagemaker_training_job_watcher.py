from datetime import datetime

import boto3
import pytest
from botocore.stub import Stubber
from botocore.client import ClientError
from pytest import fixture

from bai_watcher.sage_maker_job_watcher import SageMakerTrainingJobWatcher
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

MOCKED_REGION = "us-east-1"


@fixture
def sagemaker_client():
    sagemaker_client = boto3.client("sagemaker", region_name=MOCKED_REGION)
    return sagemaker_client


def sm_job_description(primary_status: str, secondary_status: str):
    return {
        "TrainingJobStatus": primary_status,
        "SecondaryStatus": secondary_status,
        "TrainingJobName": "name",
        "TrainingJobArn": "arn",
        "ModelArtifacts": {"S3ModelArtifacts": "s3stuff"},
        "AlgorithmSpecification": {"TrainingInputMode": "mode"},
        "ResourceConfig": {"InstanceType": "", "InstanceCount": 1, "VolumeSizeInGB": 30},
        "StoppingCondition": {},
        "CreationTime": datetime.now(),
    }


@pytest.mark.parametrize(
    ["primary_status", "secondary_status", "expected_benchmark_status"],
    [
        ("InProgress", "Starting", BenchmarkJobStatus.SM_IN_PROGRESS_STARTING),
        ("InProgress", "LaunchingMLInstances", BenchmarkJobStatus.SM_IN_PROGRESS_LAUNCHING_ML_INSTANCES),
        ("InProgress", "PreparingTrainingStack", BenchmarkJobStatus.SM_IN_PROGRESS_PREP_TRAINING_STACK),
        ("InProgress", "Downloading", BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING),
        ("InProgress", "DownloadingTrainingImage", BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING_TRAINING_IMG),
        ("InProgress", "Training", BenchmarkJobStatus.SM_IN_PROGRESS_TRAINING),
        ("Stopped", "Stopped", BenchmarkJobStatus.SM_STOPPED),
        ("Stopping", "Stopping", BenchmarkJobStatus.SM_STOPPING),
        ("Failed", "MaxRuntimeExceeded", BenchmarkJobStatus.SM_FAILED_MAX_RUNTIME_EXCEEDED),
        ("Failed", "MaxWaitTimeExceeded", BenchmarkJobStatus.SM_FAILED_MAX_WAITTIME_EXCEEDED),
        ("Failed", "Interrupted", BenchmarkJobStatus.SM_INTERRUPTED),
        ("Completed", "Completed", BenchmarkJobStatus.SUCCEEDED),
        ("Failed", "Failed", BenchmarkJobStatus.FAILED),
        # Ensure primary status is also taken into account in case the secondary
        # isn't recognized
        ("Completed", "N/A", BenchmarkJobStatus.SUCCEEDED),
        ("Stopped", "N/A", BenchmarkJobStatus.SM_STOPPED),
        ("Stopping", "N/A", BenchmarkJobStatus.SM_STOPPED),
        ("Failed", "N/A", BenchmarkJobStatus.FAILED),
        # Completely unknown statuses are unknown
        ("N/A", "N/A", BenchmarkJobStatus.SM_UNKNOWN),
    ],
)
def test_corret_status_is_returned(primary_status, secondary_status, expected_benchmark_status, sagemaker_client):
    stub = Stubber(sagemaker_client)
    stub.add_response(
        method="describe_training_job", service_response=sm_job_description(primary_status, secondary_status)
    )
    stub.activate()

    watcher = SageMakerTrainingJobWatcher("job_id", None, sagemaker_client=sagemaker_client)
    assert watcher._get_status() == expected_benchmark_status


def test_returns_job_not_found(sagemaker_client):
    stub = Stubber(sagemaker_client)
    stub.add_client_error(
        "describe_training_job",
        service_error_code="ValidationException",
        service_message="Requested resource not found.",
        expected_params={"TrainingJobName": "job_id"},
    )
    stub.activate()

    watcher = SageMakerTrainingJobWatcher("job_id", None, sagemaker_client=sagemaker_client)
    assert watcher._get_status() == BenchmarkJobStatus.JOB_NOT_FOUND


def test_raises_exceptions(sagemaker_client):
    stub = Stubber(sagemaker_client)
    stub.add_client_error(
        "describe_training_job",
        service_error_code="ValidationException",
        service_message="Requested resource has a problem.",
        expected_params={"TrainingJobName": "job_id"},
    )
    stub.activate()
    watcher = SageMakerTrainingJobWatcher("job_id", None, sagemaker_client=sagemaker_client)
    with pytest.raises(ClientError):
        watcher._get_status()
