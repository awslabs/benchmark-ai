from typing import Any

from bai_kafka_utils.events import BenchmarkEvent

from bai_kafka_utils.kafka_service import KafkaServiceCallback


class KafkaCommandCallback(KafkaServiceCallback):
    def __init__(self, object: Any, cmd_return_topic: str):
        self.object = object
        self.cmd_return_topic = cmd_return_topic

    def handle_event(self, event: BenchmarkEvent, kafka_service):

        pass

    def cleanup(self):
        pass
