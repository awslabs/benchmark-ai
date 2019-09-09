import logging

from typing import Dict

from bai_kafka_utils.events import CommandRequestEvent
from bai_kafka_utils.executors.execution_callback import (
    ExecutionEngine,
    Status,
    ExecutionEngineException,
    NoResourcesFoundException,
)
from bai_kafka_utils.kafka_service import KafkaService

logger = logging.getLogger(__name__)


class ExecutorCommandObject:
    def __init__(self, execution_engines: Dict[str, ExecutionEngine]):
        self.execution_engines = execution_engines

    def cancel(
        self,
        kafka_service: KafkaService,
        event: CommandRequestEvent,
        client_id: str,
        target_action_id: str,
        cascade: bool = False,
    ):
        for engine in set(self.execution_engines.values()):
            try:
                result = engine.cancel(client_id, target_action_id, cascade)
            except ExecutionEngineException as err:
                if isinstance(err, NoResourcesFoundException):
                    logger.info(f"No resources found for {target_action_id}")
                else:
                    kafka_service.send_status_message_event(
                        event,
                        Status.FAILED,
                        f"An error occurred when attempting to delete resources related to {target_action_id}. "
                        f"Please check the status of the deletion command ({event.action_id} "
                        f"for additional information.",
                        target_action_id,
                    )
                raise err

            # issue event under the target action_id
            kafka_service.send_status_message_event(
                event, Status.SUCCEEDED, "Execution successfully cancelled...", target_action_id
            )

            return result
