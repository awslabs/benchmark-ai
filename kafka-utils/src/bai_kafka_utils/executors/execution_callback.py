import abc
import logging

from typing import Dict, List

from bai_kafka_utils.events import (
    FetcherBenchmarkEvent,
    ExecutorPayload,
    ExecutorBenchmarkEvent,
    create_from_object,
    Status,
    BenchmarkJob,
)
from bai_kafka_utils.executors.descriptor import SINGLE_RUN_SCHEDULING
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceCallbackException

logger = logging.getLogger(__name__)


class ExecutionEngine(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def run(self, event: FetcherBenchmarkEvent) -> BenchmarkJob:
        pass

    @abc.abstractmethod
    def cancel(self, client_id: str, action_id: str, cascade: bool = False):
        pass


class ExecutionEngineException(Exception):
    pass


class ExecutorEventHandler(KafkaServiceCallback):
    DEFAULT_ENGINE = "default"

    def __init__(
        self, execution_engines: Dict[str, ExecutionEngine], valid_execution_engines: List[str], producer_topic: str
    ):
        self.producer_topic = producer_topic
        self.execution_engines = execution_engines
        self.valid_execution_engines = valid_execution_engines

    def handle_event(self, event: FetcherBenchmarkEvent, kafka_service: KafkaService):

        # Only handle single run benchmarks
        if not ExecutorEventHandler.is_single_run(event):
            logging.debug(f"Ignoring non single-run event: {event}")
            return

        engine_id = ExecutorEventHandler.get_engine_id(event)
        engine = self.execution_engines.get(engine_id)

        if not engine:

            # Ok. I've failed, but may be another service can have this engine
            if engine_id not in self.valid_execution_engines:
                # It's really something weird
                kafka_service.send_status_message_event(event, Status.ERROR, f"Unknown engine {engine_id}")
            return

        try:
            job = engine.run(event)
        except ExecutionEngineException as e:
            logger.exception("Engine throws exception")
            kafka_service.send_status_message_event(event, Status.ERROR, str(e))
            raise KafkaServiceCallbackException from e

        payload = ExecutorPayload.create_from_fetcher_payload(event.payload, job)

        response_event = create_from_object(ExecutorBenchmarkEvent, event, payload=payload)

        kafka_service.send_status_message_event(
            response_event, Status.SUCCEEDED, f"Benchmark successfully submitted with job id {job.id}"
        )
        kafka_service.send_event(response_event, topic=self.producer_topic)

    @staticmethod
    def get_engine_id(event):
        return event.payload.toml.contents.get("info", {}).get("execution_engine", ExecutorEventHandler.DEFAULT_ENGINE)

    @staticmethod
    def is_single_run(event):
        scheduling = event.payload.toml.contents.get("info", {}).get("scheduling", SINGLE_RUN_SCHEDULING)
        return scheduling == SINGLE_RUN_SCHEDULING

    def cleanup(self):
        pass
