import pytest
from pytest import fixture
from typing import Dict
from unittest.mock import create_autospec, ANY

from bai_kafka_utils.events import (
    FetcherBenchmarkEvent,
    FetcherPayload,
    BenchmarkDoc,
    create_from_object,
    BenchmarkEvent,
    BenchmarkJob,
    ExecutorBenchmarkEvent,
    ExecutorPayload,
    Status,
)
from bai_kafka_utils.execution_callback import ExecutorEventHandler, ExecutionEngine, ExecutionEngineException
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceCallbackException

JOB_ID = "ID"

ENGINE_2_ID = "ENG2"

ENGINE_1_ID = "ENG1"

REMOTE_ENGINE_ID = "REMOTE"

VALID_ENGINES = [ENGINE_1_ID, ENGINE_2_ID, REMOTE_ENGINE_ID]

PRODUCER_TOPIC = "TOPIC"

BENCHMARK_JOB = BenchmarkJob(JOB_ID)


@fixture
def engine1():
    return create_engine_mock()


def create_engine_mock():
    mock = create_autospec(ExecutionEngine)
    mock.run.return_value = BENCHMARK_JOB
    return mock


@fixture
def engine2():
    return create_engine_mock()


@fixture
def execution_engines(engine1: ExecutionEngine, engine2: ExecutionEngine):
    return {ExecutorEventHandler.DEFAULT_ENGINE: engine1, ENGINE_1_ID: engine1, ENGINE_2_ID: engine2}


@fixture
def executor_handler(execution_engines: Dict[str, ExecutionEngine]):
    return ExecutorEventHandler(execution_engines, VALID_ENGINES, PRODUCER_TOPIC)


@fixture
def kafka_service():
    return create_autospec(KafkaService)


@fixture
def fetcher_event(benchmark_event: BenchmarkEvent) -> FetcherBenchmarkEvent:
    toml = BenchmarkDoc(contents={"var": "val"}, doc="DONTCARE", sha1="DONTCARE")

    return create_from_object(FetcherBenchmarkEvent, benchmark_event, payload=FetcherPayload(datasets=[], toml=toml))


@fixture
def expected_executor_event(fetcher_event: FetcherBenchmarkEvent) -> ExecutorBenchmarkEvent:
    job_payload = ExecutorPayload.create_from_fetcher_payload(fetcher_event.payload, BENCHMARK_JOB)
    return create_from_object(ExecutorBenchmarkEvent, fetcher_event, payload=job_payload)


def test_default_engine(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    engine1: ExecutionEngine,
):
    executor_handler.handle_event(fetcher_event, kafka_service)

    engine1.run.assert_called_once_with(fetcher_event)


def test_first_engine(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    engine1: ExecutionEngine,
):
    given_engine(fetcher_event, ENGINE_1_ID)

    executor_handler.handle_event(fetcher_event, kafka_service)

    engine1.run.assert_called_once_with(fetcher_event)


def given_engine(fetcher_event: FetcherBenchmarkEvent, engine_id):
    fetcher_event.payload.toml.contents["info"] = {"execution_engine": engine_id}


def test_second_engine(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    engine2: ExecutionEngine,
):
    given_engine(fetcher_event, ENGINE_2_ID)

    executor_handler.handle_event(fetcher_event, kafka_service)

    engine2.run.assert_called_once_with(fetcher_event)


def test_remote_engine(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    engine1: ExecutionEngine,
    engine2: ExecutionEngine,
):
    given_engine(fetcher_event, REMOTE_ENGINE_ID)

    executor_handler.handle_event(fetcher_event, kafka_service)

    kafka_service.send_status_message_event.assert_not_called()
    kafka_service.send_event.assert_not_called()
    engine1.run.assert_not_called()
    engine2.run.assert_not_called()


def test_invalid_engine(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    engine1: ExecutionEngine,
    engine2: ExecutionEngine,
):
    given_engine(fetcher_event, "INVALID")

    executor_handler.handle_event(fetcher_event, kafka_service)

    kafka_service.send_status_message_event.assert_called_once_with(fetcher_event, Status.ERROR, ANY)
    kafka_service.send_event.assert_not_called()
    engine1.run.assert_not_called()
    engine2.run.assert_not_called()


def test_handle_event(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    expected_executor_event: ExecutorBenchmarkEvent,
):
    executor_handler.handle_event(fetcher_event, kafka_service)

    kafka_service.send_event.assert_called_once_with(expected_executor_event, PRODUCER_TOPIC)
    kafka_service.send_status_message_event.assert_called_once_with(expected_executor_event, Status.SUCCEEDED, ANY)


def test_run_raises(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    engine1: ExecutionEngine,
):
    engine1.run.side_effect = ExecutionEngineException("Oops")

    with pytest.raises(KafkaServiceCallbackException):
        executor_handler.handle_event(fetcher_event, kafka_service)

    kafka_service.send_status_message_event.assert_called_once_with(fetcher_event, Status.ERROR, ANY)
    kafka_service.send_event.assert_not_called()
