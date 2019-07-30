import logging

import sagemaker
from bai_kafka_utils.executors.execution_callback import ExecutorEventHandler

from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name

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
    exec_handler = ExecutorEventHandler(
        execution_engines, sagemaker_config.valid_execution_engines, common_kafka_cfg.producer_topic
    )

    callbacks = {common_kafka_cfg.consumer_topic: [exec_handler]}

    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, SERVICE_NAME)

    pod_name = get_pod_name()

    return KafkaService(
        name=SERVICE_NAME,
        version=__version__,
        callbacks=callbacks,
        kafka_consumer=consumer,
        kafka_producer=producer,
        pod_name=pod_name,
        status_topic=common_kafka_cfg.status_topic,
    )
