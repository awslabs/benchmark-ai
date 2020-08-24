import json
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
            logger.exception("Could not parse descriptor %s", e)
            raise ExecutionEngineException("Cannot process the request") from e

        with tempfile.TemporaryDirectory(prefix=self.config.tmp_sources_dir) as tmpdirname:
            ScriptSourceDirectory.create(descriptor, tmpdirname, event.payload.scripts)

            session = self.session_factory()
            try:
                estimator = self.estimator_factory(session, descriptor, tmpdirname, self.config)
            except Exception as e:
                logger.exception("Could not create estimator %s", e)
                raise ExecutionEngineException("Cannot create estimator") from e

            # Estimate the total size
            total_size_gb = self._estimate_total_gb(event)
            estimator.train_volume_size = max(estimator.train_volume_size, total_size_gb)

            data = self._get_estimator_data(event)

            try:
                job_name = SageMakerExecutionEngine._get_job_name(event.action_id)
                merge = False
                if descriptor.custom_params and descriptor.custom_params.sagemaker_job_name:
                    job_name = descriptor.custom_params.sagemaker_job_name
                if descriptor.custom_params and descriptor.custom_params.merge:
                    merge = descriptor.custom_params.merge
                logger.info(f"Attempting to start training job {job_name}")
                if merge:
                    estimator.fit(data, wait=True, logs=False, job_name=job_name)
                    self.merge_metrics(descriptor)
                else:
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

    def merge_metrics(self, descriptor):
        """
        Will create a cloudwatch metric under ANUBIS/METRICS with dimensions provided by descriptor.info.labels
        :param descriptor: Descriptor object that is generated from reading submited toml file
        :return: N/A
        """
        job_name = descriptor.custom_params.sagemaker_job_name
        logger.info(f"Attempting to merge metrics for training job {job_name}")
        cloudwatch_client = boto3.client("cloudwatch")
        data = {}
        # TrainingJob may finish but the metrics may have not been uploaded yet
        # Will loop until the FinalMetricDataList is populated
        while "FinalMetricDataList" not in data:
            data = self.sagemaker_client.describe_training_job(TrainingJobName=job_name)
        metric_data = self.tag_dimensions(descriptor, data["FinalMetricDataList"])
        cloudwatch_client.put_metric_data(Namespace="ANUBIS/METRICS", MetricData=metric_data)
        if "dashboard-name" in descriptor.custom_params.dashboard:
            logger.info("IF worked")
            pre_existing_dashboard = False
            existing_dashboards = self.cloudwatch.list_dashboards()
            for dashboard in existing_dashboards["DashboardEntries"]:
                if dashboard["DashboardName"] == descriptor.custom_params.dashboard:
                    pre_existing_dashboard = True
            if pre_existing_dashboard:
                logger.info("We made it to update")
                self.update_dashboard(descriptor.info.labels, descriptor.custom_params.dashboard)
            else:
                logger.info("We made it to create")
                self.create_dashboard(descriptor.info.labels)

    def update_dashboard(self, labels, dashboard_name):
        dashboard = self.cloudwatch.get_dashboard(DashboardName=dashboard_name)
        dashboard_body = json.loads(dashboard["DashboardBody"])
        metric = ["ANUBIS/METRICS", labels["task_name"]]
        for name, val in labels.items():
            metric.append(name)
            metric.append(val)
        for widget in dashboard_body["widgets"]:
            properties = widget["properties"]
            if "metrics" in properties and properties["metrics"][0] == metric:
                return
        dashboard_body["widgets"].append(
            {
                "type": "metric",
                "properties": {
                    "metrics": [metric],
                    "region": "us-east-1",
                    "title": labels["task_name"],
                    "period": 86400,
                },
            }
        )
        updated_dashboard_body = json.dumps(dashboard_body)
        retVal = self.cloudwatch.put_dashboard(DashboardName=dashboard_name, DashboardBody=updated_dashboard_body)
        logger.info(retVal)

    def create_dashboard(self, labels, dashboard_name):
        metric = ["ANUBIS/METRICS", dashboard_name]
        for name, val in labels.items():
            metric.append(name)
            metric.append(val)
        new_dashboard = {
            "widgets": [
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [metric],
                        "region": "us-east-1",
                        "title": labels["task_name"],
                        "period": 86400,
                    },
                }
            ]
        }
        dashboard_as_json = json.dumps(new_dashboard)
        retVal = self.cloudwatch_client.put_dashboard(DashboardName=dashboard_name, DashboardBody=dashboard_as_json)
        logger.info(retVal)

    def tag_dimensions(self, descriptor, metric_data):
        """
        Using the descrriptor's info.labels will populate a dimensions object and create the metric_data object
        :param descriptor: Descriptor object that is generated from reading submited toml file
        :param metric_data: The base metric_data that is returned by the sagemaker_client_describe_training_job
        :return: Returns the formulated final metric_data object that contains all the dimensions provided by the user
        """
        # Metric formatting in seperate method
        # Easier to debug/test
        dimensions = []
        # Pass in Names/Values to cloudwatch dimensions this matches non SM Anubis Behavior
        for name in descriptor.info.labels:
            dimensions.append({"Name": name, "Value": descriptor.info.labels[name]})
        # Timestamp field gets auto-populated with incorrect timestamps
        # Pop them to make timestamp default to time of put_metric_data call
        for metric in metric_data:
            metric.pop("Timestamp")
            metric["Dimensions"] = dimensions
        return metric_data

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
            logging.exception(f"Could not stop training job {action_id} %s", err)
            if is_not_found_error(err):
                raise NoResourcesFoundException(action_id) from err
            raise ExecutionEngineException(str(err)) from err
        logging.info(f"Successfully issued stop training command for {action_id}")
