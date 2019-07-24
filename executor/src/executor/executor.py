import logging

from bai_kafka_utils.cmd_callback import KafkaCommandCallback
from bai_kafka_utils.executors.execution_callback import ExecutorEventHandler
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig
from bai_kafka_utils.utils import get_pod_name

from executor import SERVICE_NAME, __version__
from executor.commands import ExecutorCommandObject
from executor.config import ExecutorConfig
from executor.k8s_execution_engine import K8SExecutionEngine

logger = logging.getLogger(SERVICE_NAME)


def create_execution_engines(executor_config: ExecutorConfig):
    k8s_engine = K8SExecutionEngine(executor_config)
    return {ExecutorEventHandler.DEFAULT_ENGINE: k8s_engine, K8SExecutionEngine.ENGINE_ID: k8s_engine}


def create_executor(common_kafka_cfg: KafkaServiceConfig, executor_config: ExecutorConfig) -> KafkaService:
    cmd_object = ExecutorCommandObject(executor_config.kubectl)

    execution_engines = create_execution_engines(executor_config)
    exec_handler = ExecutorEventHandler(
        execution_engines, executor_config.valid_execution_engines, common_kafka_cfg.producer_topic
    )

    callbacks = {
        common_kafka_cfg.consumer_topic: [exec_handler],
        common_kafka_cfg.cmd_submit_topic: [
            KafkaCommandCallback(cmd_object=cmd_object, cmd_return_topic=common_kafka_cfg.cmd_return_topic)
        ],
    }

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
