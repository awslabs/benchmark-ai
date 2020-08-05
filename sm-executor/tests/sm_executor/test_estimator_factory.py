import json

import pytest
from bai_kafka_utils.executors.descriptor import BenchmarkDescriptor, DistributedStrategy
from mock import PropertyMock
from pytest import fixture
from sagemaker import Session
from sagemaker.estimator import Framework
from sagemaker.tensorflow import TensorFlow

from sm_executor import estimator_factory
from sm_executor.args import SageMakerExecutorConfig
from sm_executor.estimator_factory import (
    create_estimator,
    EstimatorFactory,
    create_tensorflow_estimator,
    create_mxnet_estimator,
)
from sm_executor.source_dir import ScriptSourceDirectory

SOURCE_DIR = "/tmp/somedir/this"


@fixture
def mock_create_tensorflow_estimator(mocker) -> EstimatorFactory:
    return mocker.patch.object(estimator_factory, "create_tensorflow_estimator", autoSpec=True)


@fixture
def mock_create_mxnet_estimator(mocker) -> EstimatorFactory:
    return mocker.patch.object(estimator_factory, "create_mxnet_estimator", autoSpec=True)


@fixture
def mock_session(mocker) -> Session:
    mock = mocker.create_autospec(Session)
    mock.local_mode = PropertyMock(return_value=False)
    mock.config = "A"
    return mock


def test_estimator_factory_routing(
    mock_session: Session,
    descriptor: BenchmarkDescriptor,
    sagemaker_config: SageMakerExecutorConfig,
    mock_create_tensorflow_estimator: EstimatorFactory,
    mock_create_mxnet_estimator: EstimatorFactory,
):
    create_estimator(mock_session, descriptor, SOURCE_DIR, sagemaker_config)

    mock_create_mxnet_estimator.assert_not_called()
    mock_create_tensorflow_estimator.assert_called_once()


def validate_estimator_common(
    estimator: Framework, mock_session: Session, descriptor, sagemaker_config: SageMakerExecutorConfig
):
    assert estimator.source_dir == SOURCE_DIR
    assert estimator.entry_point == ScriptSourceDirectory.PYTHON_ENTRY_POINT
    assert estimator.sagemaker_session == mock_session
    assert estimator.image_name == descriptor.env.docker_image
    assert estimator.framework_version == descriptor.ml.framework_version
    assert estimator.train_instance_type == descriptor.hardware.instance_type
    assert estimator.train_instance_count == descriptor.hardware.distributed.num_instances
    assert estimator.role == sagemaker_config.sm_role
    assert estimator.output_path == f"s3://{sagemaker_config.s3_output_bucket}"
    assert estimator.security_group_ids == sagemaker_config.security_group_ids
    assert estimator.subnets == sagemaker_config.subnets


def validate_estimator_tensorflow(
    estimator: TensorFlow, mock_session: Session, descriptor, sagemaker_config: SageMakerExecutorConfig
):
    assert estimator.script_mode
    if descriptor.hardware.strategy == DistributedStrategy.SINGLE_NODE:
        assert not estimator.distributions
    elif descriptor.hardware.strategy == DistributedStrategy.HOROVOD:
        assert estimator.distributions.mpi["enabled"]
        assert estimator.distributions.mpi["processes_per_host"] == descriptor.processes_per_instance


def validate_estimator_hyperparams(
    estimator: Framework, mock_session: Session, descriptor, sagemaker_config: SageMakerExecutorConfig
):
    assert estimator.hyperparameters()
    assert estimator.source_dir == SOURCE_DIR
    assert estimator.entry_point == ScriptSourceDirectory.PYTHON_ENTRY_POINT
    assert estimator.sagemaker_session == mock_session
    assert estimator.image_name == descriptor.env.docker_image
    assert estimator.framework_version == descriptor.ml.framework_version
    assert estimator.train_instance_type == descriptor.hardware.instance_type
    assert estimator.train_instance_count == descriptor.hardware.distributed.num_instances
    assert estimator.role == sagemaker_config.sm_role
    assert estimator.output_path == f"s3://{sagemaker_config.s3_output_bucket}"
    assert estimator.security_group_ids == sagemaker_config.security_group_ids
    assert estimator.subnets == sagemaker_config.subnets


@pytest.mark.parametrize("strategy", [DistributedStrategy.SINGLE_NODE, DistributedStrategy.HOROVOD])
def test_estimator_factory_tensorflow(
    mock_session: Session,
    descriptor: BenchmarkDescriptor,
    sagemaker_config: SageMakerExecutorConfig,
    strategy: DistributedStrategy,
):
    descriptor.strategy = strategy
    estimator = create_tensorflow_estimator(mock_session, descriptor, SOURCE_DIR, sagemaker_config)
    validate_estimator_common(estimator, mock_session, descriptor, sagemaker_config)
    validate_estimator_tensorflow(estimator, mock_session, descriptor, sagemaker_config)


def test_estimator_factory_mxnet(
    mock_session: Session, descriptor: BenchmarkDescriptor, sagemaker_config: SageMakerExecutorConfig
):
    estimator = create_mxnet_estimator(mock_session, descriptor, SOURCE_DIR, sagemaker_config)
    validate_estimator_common(estimator, mock_session, descriptor, sagemaker_config)


@pytest.mark.parametrize("strategy", [DistributedStrategy.SINGLE_NODE, DistributedStrategy.HOROVOD])
def test_estimator_factory_hyperparams_tensorflow(
    mock_session: Session,
    hyperparams_descriptor: BenchmarkDescriptor,
    sagemaker_config: SageMakerExecutorConfig,
    strategy: DistributedStrategy,
):
    hyperparams_descriptor.strategy = strategy
    estimator = create_tensorflow_estimator(mock_session, hyperparams_descriptor, SOURCE_DIR, sagemaker_config)
    validate_estimator_hyperparams(estimator, mock_session, hyperparams_descriptor, sagemaker_config)

def test_estimator_factory_mxnet(
    mock_session: Session, hyperparams_descriptor: BenchmarkDescriptor, sagemaker_config: SageMakerExecutorConfig
):
    estimator = create_mxnet_estimator(mock_session, hyperparams_descriptor, SOURCE_DIR, sagemaker_config)
    validate_estimator_hyperparams(estimator, mock_session, hyperparams_descriptor, sagemaker_config)

