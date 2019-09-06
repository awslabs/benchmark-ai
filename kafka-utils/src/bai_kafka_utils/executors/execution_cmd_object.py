import dataclasses
from typing import Dict

from bai_kafka_utils.events import CommandRequestEvent
from bai_kafka_utils.executors.execution_callback import ExecutionEngine, Status
from bai_kafka_utils.kafka_service import KafkaService


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
            engine.cancel(client_id, target_action_id, cascade)

            # issue event under the target action_id
            kafka_service.send_status_message_event(
                event, Status.SUCCEEDED, "Execution successfully cancelled...", target_action_id
            )
