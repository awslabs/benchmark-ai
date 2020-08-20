from __future__ import annotations

from typing import Callable, Dict, Any

from bai_sagemaker_utils.utils import is_not_found_error
from botocore.client import ClientError

from bai_watcher import service_logger
from bai_watcher.job_watcher import JobWatcher
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

logger = service_logger.getChild(__name__)

SLEEP_TIME_BETWEEN_CHECKING_SAGEMAKER_STATUS = 10


class SageMakerTrainingJobWatcher(JobWatcher):
    def __init__(self, job_id: str, callback: Callable[[str, BenchmarkJobStatus], bool], *, sagemaker_client):
        super().__init__(job_id, callback, SLEEP_TIME_BETWEEN_CHECKING_SAGEMAKER_STATUS)
        self._sagemaker_client = sagemaker_client

    @staticmethod
    def _get_benchmark_status(training_job: Dict[str, Any]):
        primary_status = training_job["TrainingJobStatus"]
        secondary_status = training_job["SecondaryStatus"]
        if secondary_status == "Starting":
            return BenchmarkJobStatus.SM_IN_PROGRESS_STARTING
        elif secondary_status == "LaunchingMLInstances":
            return BenchmarkJobStatus.SM_IN_PROGRESS_LAUNCHING_ML_INSTANCES
        elif secondary_status == "PreparingTrainingStack":
            return BenchmarkJobStatus.SM_IN_PROGRESS_PREP_TRAINING_STACK
        elif secondary_status == "Downloading":
            return BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING
        elif secondary_status == "DownloadingTrainingImage":
            return BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING_TRAINING_IMG
        elif secondary_status == "Training":
            return BenchmarkJobStatus.SM_IN_PROGRESS_TRAINING
        elif secondary_status == "Stopped":
            return BenchmarkJobStatus.SM_STOPPED
        elif secondary_status == "Stopping":
            return BenchmarkJobStatus.SM_STOPPING
        elif secondary_status == "MaxRuntimeExceeded":
            return BenchmarkJobStatus.SM_FAILED_MAX_RUNTIME_EXCEEDED
        elif secondary_status == "MaxWaitTimeExceeded":
            return BenchmarkJobStatus.SM_FAILED_MAX_WAITTIME_EXCEEDED
        elif secondary_status == "Uploading":
            return BenchmarkJobStatus.SM_IN_PROGRESS_UPLOADING
        elif secondary_status == "Interrupted":
            return BenchmarkJobStatus.SM_INTERRUPTED
        elif secondary_status == "Completed":
            return BenchmarkJobStatus.SUCCEEDED
        elif secondary_status == "Failed":
            return BenchmarkJobStatus.FAILED

        logger.info(f"Could not decode secondary status {secondary_status} - trying primary: {primary_status}")
        if primary_status == "Failed":
            return BenchmarkJobStatus.FAILED
        elif primary_status == "Completed":
            return BenchmarkJobStatus.SUCCEEDED
        elif primary_status == "Stopped":
            return BenchmarkJobStatus.SM_STOPPED
        elif primary_status == "Stopping":
            return BenchmarkJobStatus.SM_STOPPED

        logger.warning(f"Could not decode SageMaker training job secondary_status {primary_status}/{secondary_status}")
        return BenchmarkJobStatus.SM_UNKNOWN

    def _get_status(self):
        try:
            training_job = self._sagemaker_client.describe_training_job(TrainingJobName=self._job_id)
            return self._get_benchmark_status(training_job)
        except ClientError as err:
            if is_not_found_error(err):
                return BenchmarkJobStatus.JOB_NOT_FOUND
            logger.exception(
                "Unknown error from SageMaker, stopping thread that watches job {job_id} with an exception".format(
                    job_id=self._job_id
                )
            )
            raise err
