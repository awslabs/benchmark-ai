import logging
import re
import tempfile
from math import ceil
from typing import Callable

import boto3
import botocore
import sagemaker
from bai_kafka_utils.events import FetcherBenchmarkEvent, BenchmarkJob
from bai_kafka_utils.executors.descriptor import DescriptorConfig, Descriptor, DescriptorError
from bai_kafka_utils.executors.execution_callback import (
    ExecutionEngine,
    ExecutionEngineException,
    NoResourcesFoundException,
)
from botocore.exceptions import ClientError

from sm_executor.args import SageMakerExecutorConfig
from sm_executor.estimator_factory import EstimatorFactory, TENSORFLOW_FRAMEWORK, MXNET_FRAMEWORK
from sm_executor.source_dir import ScriptSourceDirectory

CONFIG = DescriptorConfig(["single_node", "horovod"], [TENSORFLOW_FRAMEWORK, MXNET_FRAMEWORK])

SageMakerSessionFactory = Callable[[], sagemaker.Session]


logger = logging.getLogger(__name__)


class SageMakerExecutionEngine(ExecutionEngine):
    ENGINE_ID = "aws.sagemaker"

    SAFETY_FACTOR = 1.1

    def __init__(
        self,
        session_factory: SageMakerSessionFactory,
        estimator_factory: EstimatorFactory,
        config: SageMakerExecutorConfig,
        sagemaker_client=None,
    ):
        self.session_factory = session_factory
        self.estimator_factory = estimator_factory
        self.config = config

        self.sagemaker_client = sagemaker_client or boto3.client("sagemaker")

    @staticmethod
    def _get_job_name(action_id: str):
        return action_id

    def run(self, event: FetcherBenchmarkEvent) -> BenchmarkJob:
        try:
            descriptor = Descriptor(event.payload.toml.contents, CONFIG)
        except DescriptorError as e:
            raise ExecutionEngineException("Cannot process the request") from e

        with tempfile.TemporaryDirectory(prefix=self.config.tmp_sources_dir) as tmpdirname:
            ScriptSourceDirectory.create(descriptor, tmpdirname, event.payload.scripts)

            session = self.session_factory()

            try:
                estimator = self.estimator_factory(session, descriptor, tmpdirname, self.config)
            except Exception as e:
                raise ExecutionEngineException("Cannot create estimator") from e

            # Estimate the total size
            total_size_gb = self._estimate_total_gb(event)
            estimator.train_volume_size = max(estimator.train_volume_size, total_size_gb)

            data = self._get_estimator_data(event)

            try:
                job_name = SageMakerExecutionEngine._get_job_name(event.action_id)
                estimator.fit(data, wait=False, logs=False, job_name=job_name)
            except botocore.exceptions.ClientError as e:
                raise ExecutionEngineException("Cannot execute the requested benchmark") from e
            return BenchmarkJob(id=estimator.latest_training_job.name)

    def _get_estimator_data(self, event):
        def _get_dataset_id(inx, id):
            return id or f"src{inx}"

        data = {_get_dataset_id(inx, dataset.id): dataset.dst for inx, dataset in enumerate(event.payload.datasets)}
        if not data:
            data[_get_dataset_id(0, None)] = self.config.s3_nodata
        return data

    @staticmethod
    def _estimate_total_gb(event):
        total_size = sum([dataset.size_info.total_size for dataset in event.payload.datasets])
        total_size_gb = int(SageMakerExecutionEngine.SAFETY_FACTOR * ceil(total_size / 1024 ** 3))
        return total_size_gb

    @staticmethod
    def _is_not_found_error(client_error: ClientError):
        error_message = client_error.response.get("Error", {}).get("Message", "")
        return re.match(r"(\w*\s*)*not found(\s*\w*)*", error_message, re.IGNORECASE) is not None

    def cancel(self, client_id: str, action_id: str, cascade: bool = False):
        job_name = SageMakerExecutionEngine._get_job_name(action_id)
        try:
            self.sagemaker_client.stop_training_job(TrainingJobName=job_name)
        except botocore.exceptions.ClientError as err:
            if self._is_not_found_error(err):
                raise NoResourcesFoundException(action_id) from err
            raise ExecutionEngineException(str(err)) from err
