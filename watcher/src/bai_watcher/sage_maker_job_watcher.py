from __future__ import annotations

from typing import Callable, Dict, Any

import botocore
from bai_sagemaker_utils.utils import is_not_found_error

from bai_watcher import service_logger
from bai_watcher.job_watcher import JobWatcher
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

logger = service_logger.getChild(__name__)

SLEEP_TIME_BETWEEN_CHECKING_SAGEMAKER_STATUS = 10


class SageMakerTrainingJobWatcher(JobWatcher):
    def __init__(
        self,
        job_id: str,
        callback: Callable[[str, BenchmarkJobStatus, SageMakerTrainingJobWatcher], bool],
        *,
        sagemaker_client
    ):
        super().__init__(job_id, callback, SLEEP_TIME_BETWEEN_CHECKING_SAGEMAKER_STATUS)
        self._sagemaker_client = sagemaker_client

    @staticmethod
    def _get_benchmark_status(training_job: Dict[str, Any]):
        # 'Starting'|'LaunchingMLInstances'|'PreparingTrainingStack'|'Downloading'|'DownloadingTrainingImage'|'Training'|'Uploading'|'Stopping'|'Stopped'|'MaxRuntimeExceeded'|'Completed'|'Failed'|'Interrupted'|'MaxWaitTimeExceeded',
        status = training_job["SecondaryStatus"]
        if status == "Starting":
            return BenchmarkJobStatus.SM_IN_PROGRESS_STARTING
        elif status == "LaunchingMLInstances":
            return BenchmarkJobStatus.SM_IN_PROGRESS_LAUNCHING_ML_INSTANCES
        elif status == "PreparingTrainingStack":
            return BenchmarkJobStatus.SM_IN_PROGRESS_PREP_TRAINING_STACK
        elif status == "Downloading":
            return BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING
        elif status == "DownloadingTrainingImage":
            return BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING_TRAINING_IMG
        elif status == "Training":
            return BenchmarkJobStatus.SM_IN_PROGRESS_TRAINING
        elif status == "Stopped":
            return BenchmarkJobStatus.SM_STOPPED
        elif status == "Stopping":
            return BenchmarkJobStatus.SM_STOPPING
        elif status == "MaxRuntimeExceeded":
            return BenchmarkJobStatus.SM_FAILED_MAX_RUNTIME_EXCEEDED
        elif status == "MaxWaitTimeExceeded":
            return BenchmarkJobStatus.SM_FAILED_MAX_WAITTIME_EXCEEDED
        elif status == "Interrupted":
            return BenchmarkJobStatus.SM_INTERRUPTED
        elif status == "Completed":
            return BenchmarkJobStatus.SUCCEEDED
        else:
            return BenchmarkJobStatus.SM_UNKNOWN

    def _get_status(self):
        try:
            training_job = self._sagemaker_client.describe_training_job(TrainingJobName=self._job_id)
            return self._get_benchmark_status(training_job)
        except botocore.exceptions.ClientError as err:
            if is_not_found_error(err):
                return BenchmarkJobStatus.JOB_NOT_FOUND
            logger.exception(
                "Unknown error from SageMaker, stopping thread that watches job {job_id} with an exception".format(
                    job_id=self._job_id
                )
            )
            raise
