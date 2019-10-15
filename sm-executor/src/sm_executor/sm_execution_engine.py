import logging
import tempfile
from math import ceil
from typing import Callable

import boto3
import botocore
import sagemaker
from bai_kafka_utils.events import FetcherBenchmarkEvent, BenchmarkJob
from bai_kafka_utils.executors.descriptor import DescriptorConfig, BenchmarkDescriptor, DescriptorError
from bai_kafka_utils.executors.execution_callback import (
    ExecutionEngine,
    ExecutionEngineException,
    NoResourcesFoundException,
)
from bai_sagemaker_utils.utils import get_client_error_message, is_not_found_error

from sm_executor.args import SageMakerExecutorConfig
from sm_executor.estimator_factory import EstimatorFactory
from sm_executor.frameworks import MXNET_FRAMEWORK, TENSORFLOW_FRAMEWORK
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
        logger.info(f"Processing SageMaker benchmark {event.action_id}")
        try:
            descriptor = BenchmarkDescriptor.from_dict(event.payload.toml.contents, CONFIG)
        except DescriptorError as e:
            logger.exception(f"Could not parse descriptor", e)
            raise ExecutionEngineException("Cannot process the request") from e

        with tempfile.TemporaryDirectory(prefix=self.config.tmp_sources_dir) as tmpdirname:
            ScriptSourceDirectory.create(descriptor, tmpdirname, event.payload.scripts)

            session = self.session_factory()

            try:
                estimator = self.estimator_factory(session, descriptor, tmpdirname, self.config)
            except Exception as e:
                logger.exception(f"Could not create estimator", e)
                raise ExecutionEngineException("Cannot create estimator") from e

            # Estimate the total size
            total_size_gb = self._estimate_total_gb(event)
            estimator.train_volume_size = max(estimator.train_volume_size, total_size_gb)

            data = self._get_estimator_data(event)

            try:
                job_name = SageMakerExecutionEngine._get_job_name(event.action_id)
                logger.info(f"Attempting to start training job {job_name}")
                estimator.fit(data, wait=False, logs=False, job_name=job_name)

            except botocore.exceptions.ClientError as err:
                error_message = get_client_error_message(err, default="Unknown")
                raise ExecutionEngineException(
                    f"Benchmark creation failed. SageMaker returned error: {error_message}"
                ) from err
            except Exception as err:
                logger.exception("Caught unexpected exception", err)
                raise err
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

    def cancel(self, client_id: str, action_id: str, cascade: bool = False):
        logger.info(f"Attempting to stop training job {action_id}")
        job_name = SageMakerExecutionEngine._get_job_name(action_id)
        try:
            # TODO Remove the status check before issuing the stop training job
            # This is a stopgap solution
            # For some reason the SageMaker client is hanging when calling stop_training_job
            # against an existing, but not running, training job. This blocks the sm-executor from
            # servicing more events. Furthermore, it blocks it from committing the event. Meaning that it
            # will always be at the top of the queue - so, restarting the sm-executor has no effect.
            # This check ensures that, under most circumstances, this won't happen.
            # It's a hack, and it should be removed once we can figure out this SageMaker client issue.
            # Normally, the stop_training_job call should just raise a client exception.
            # GitHub issue: https://github.com/awslabs/benchmark-ai/issues/928
            training_job = self.sagemaker_client.describe_training_job(TrainingJobName=job_name)
            if training_job["TrainingJobStatus"] == "InProgress":
                self.sagemaker_client.stop_training_job(TrainingJobName=job_name)
            else:
                logging.info(f"""Skipping delete. Job status is {training_job["TrainingJobStatus"]}""")
        except botocore.exceptions.ClientError as err:
            logging.exception(f"Could not stop training job {action_id}", err)
            if is_not_found_error(err):
                raise NoResourcesFoundException(action_id) from err
            raise ExecutionEngineException(str(err)) from err
        logging.info(f"Successfully issued stop training command for {action_id}")
