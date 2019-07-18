import abc

from typing import Dict

from bai_kafka_utils.events import (
    FetcherBenchmarkEvent,
    ExecutorPayload,
    ExecutorBenchmarkEvent,
    create_from_object,
    Status,
    BenchmarkJob,
)
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceCallbackException


class ExecutionEngine(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def run(self, event: FetcherBenchmarkEvent) -> BenchmarkJob:
        pass

    @abc.abstractmethod
    def cancel(self, client_id: str, action_id: str):
        pass


class ExecutionEngineException(Exception):
    pass


class ExecutorEventHandler(KafkaServiceCallback):
    DEFAULT_ENGINE = "default"

    def __init__(self, execution_engines: Dict[str, ExecutionEngine], producer_topic: str):
        self.producer_topic = producer_topic
        self.execution_engines = execution_engines

    def handle_event(self, event: FetcherBenchmarkEvent, kafka_service: KafkaService):

        engine_id = ExecutorEventHandler.get_engine_id(event)
        engine = self.execution_engines.get(engine_id)

        if not engine:
            # Ok. I've failed, but may be another service will have this engine
            kafka_service.send_status_message_event(event, Status.ERROR, f"Unknown engine {engine_id}")
            return

        try:
            job = engine.run(event)
        except ExecutionEngineException as e:
            kafka_service.send_status_message_event(event, Status.ERROR, str(e))
            raise KafkaServiceCallbackException from e

        payload = ExecutorPayload.create_from_fetcher_payload(event.payload, job)

        response_event = create_from_object(ExecutorBenchmarkEvent, event, payload=payload)

        kafka_service.send_status_message_event(
            response_event, Status.SUCCEEDED, f"Benchmark successfully submitted with job id {event.action_id}"
        )
        kafka_service.send_event(response_event, topic=self.producer_topic)

    @staticmethod
    def get_engine_id(event):
        return event.payload.toml.contents.get("info", {}).get("execution_engine", ExecutorEventHandler.DEFAULT_ENGINE)

    def cleanup(self):
        pass
