from typing import Dict

from bai_kafka_utils.executors.execution_callback import ExecutionEngine


class ExecutorCommandObject:
    def __init__(self, execution_engines: Dict[str, ExecutionEngine]):
        self.execution_engines = execution_engines

    def cancel(self, client_id: str, target_action_id: str, cascade: bool):
        for engine in set(self.execution_engines.values()):
            engine.cancel(client_id, target_action_id, cascade)
