import logging

import sagemaker
from bai_kafka_utils.executors.executor_service import create_executor_service
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig

from sm_executor import SERVICE_NAME, __version__
from sm_executor.args import SageMakerExecutorConfig
from sm_executor.estimator_factory import create_estimator
from sm_executor.sm_execution_engine import SageMakerExecutionEngine

logger = logging.getLogger(SERVICE_NAME)


def create_execution_engines(sagemaker_config: SageMakerExecutorConfig):
    sm_engine = SageMakerExecutionEngine(
        session_factory=sagemaker.Session, estimator_factory=create_estimator, config=sagemaker_config
    )
    return {SageMakerExecutionEngine.ENGINE_ID: sm_engine}


def create_executor(common_kafka_cfg: KafkaServiceConfig, sagemaker_config: SageMakerExecutorConfig) -> KafkaService:
    execution_engines = create_execution_engines(sagemaker_config)
    return create_executor_service(SERVICE_NAME, __version__, common_kafka_cfg, execution_engines)
