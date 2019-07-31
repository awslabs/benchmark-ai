import logging
from typing import List, Dict


from bai_kafka_utils.cmd_callback import KafkaCommandCallback
from bai_kafka_utils.executors.execution_callback import ExecutorEventHandler, ExecutionEngine
from bai_kafka_utils.executors.execution_cmd_object import ExecutorCommandObject

from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig, KafkaServiceCallback
from bai_kafka_utils.utils import get_pod_name


logger = logging.getLogger(__name__)


def create_executor_service(
    service_name: str, version: str, common_kafka_cfg: KafkaServiceConfig, engines: Dict[str, ExecutionEngine]
) -> KafkaService:
    callbacks = _create_callbacks(common_kafka_cfg, engines)

    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, service_name)

    pod_name = get_pod_name()

    return KafkaService(
        name=service_name,
        version=version,
        callbacks=callbacks,
        kafka_consumer=consumer,
        kafka_producer=producer,
        pod_name=pod_name,
        status_topic=common_kafka_cfg.status_topic,
    )


def _create_callbacks(
    common_kafka_cfg: KafkaServiceConfig, engines: Dict[str, ExecutionEngine], valid_engines: List[str] = []
) -> Dict[str, List[KafkaServiceCallback]]:

    exec_handler = ExecutorEventHandler(engines, valid_engines, common_kafka_cfg.producer_topic)

    cmd_object = ExecutorCommandObject(engines)
    callbacks = {
        common_kafka_cfg.consumer_topic: [exec_handler],
        common_kafka_cfg.cmd_submit_topic: [
            KafkaCommandCallback(cmd_object=cmd_object, cmd_return_topic=common_kafka_cfg.cmd_return_topic)
        ],
    }
    return callbacks
