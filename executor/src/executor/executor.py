import logging

from bai_kafka_utils.executors.execution_callback import ExecutorEventHandler
from bai_kafka_utils.executors.executor_service import create_executor_service
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig

from executor import SERVICE_NAME, __version__
from executor.config import ExecutorConfig
from executor.k8s_execution_engine import K8SExecutionEngine

logger = logging.getLogger(SERVICE_NAME)


def create_execution_engines(executor_config: ExecutorConfig):
    k8s_engine = K8SExecutionEngine(executor_config)
    return {ExecutorEventHandler.DEFAULT_ENGINE: k8s_engine, K8SExecutionEngine.ENGINE_ID: k8s_engine}


def create_executor(common_kafka_cfg: KafkaServiceConfig, executor_config: ExecutorConfig) -> KafkaService:
    execution_engines = create_execution_engines(executor_config)

    return create_executor_service(SERVICE_NAME, __version__, common_kafka_cfg, execution_engines)
