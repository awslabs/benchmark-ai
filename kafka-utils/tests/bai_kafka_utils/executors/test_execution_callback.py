import pytest
from pytest import fixture
from typing import Dict
from unittest.mock import call, create_autospec, ANY

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
from bai_kafka_utils.executors.execution_callback import ExecutorEventHandler, ExecutionEngine, ExecutionEngineException
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
def no_engines_handler(execution_engines: Dict[str, ExecutionEngine]):
    return ExecutorEventHandler({}, VALID_ENGINES, PRODUCER_TOPIC)


@fixture
def kafka_service():
    return create_autospec(KafkaService)


@fixture
def fetcher_event(benchmark_event: BenchmarkEvent) -> FetcherBenchmarkEvent:
    toml = BenchmarkDoc(contents={"var": "val"}, doc="DONTCARE", sha1="DONTCARE")

    return create_from_object(FetcherBenchmarkEvent, benchmark_event, payload=FetcherPayload(datasets=[], toml=toml))


@fixture
def single_run_fetcher_event(fetcher_event: FetcherBenchmarkEvent) -> FetcherBenchmarkEvent:
    set_scheduling(fetcher_event, "single_run")
    return fetcher_event


@fixture
def scheduled_run_fetcher_event(fetcher_event: FetcherBenchmarkEvent) -> FetcherBenchmarkEvent:
    set_scheduling(fetcher_event, "*/1 * * * *")
    return fetcher_event


@fixture
def expected_executor_event(fetcher_event: FetcherBenchmarkEvent) -> ExecutorBenchmarkEvent:
    job_payload = ExecutorPayload.create_from_fetcher_payload(fetcher_event.payload, BENCHMARK_JOB)
    return create_from_object(ExecutorBenchmarkEvent, fetcher_event, payload=job_payload)


@fixture
def expected_pending_call(fetcher_event: FetcherBenchmarkEvent):
    return call(fetcher_event, Status.PENDING, ANY)


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
    set_execution_engine(fetcher_event, ENGINE_1_ID)

    executor_handler.handle_event(fetcher_event, kafka_service)

    engine1.run.assert_called_once_with(fetcher_event)


def set_execution_engine(fetcher_event: FetcherBenchmarkEvent, engine_id):
    fetcher_event.payload.toml.contents["info"] = {"execution_engine": engine_id}


def set_scheduling(fetcher_event: FetcherBenchmarkEvent, scheduling):
    fetcher_event.payload.toml.contents["info"] = {"scheduling": scheduling}


def test_second_engine(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    engine2: ExecutionEngine,
):
    set_execution_engine(fetcher_event, ENGINE_2_ID)

    executor_handler.handle_event(fetcher_event, kafka_service)

    engine2.run.assert_called_once_with(fetcher_event)


@pytest.mark.parametrize(
    ["engine_id", "expected_status"],
    [
        (ExecutorEventHandler.DEFAULT_ENGINE, Status.SUCCEEDED),
        ("INVALID", Status.ERROR),
        (REMOTE_ENGINE_ID, Status.SUCCEEDED),
    ],
)
def test_remote_engine(
    no_engines_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    engine1: ExecutionEngine,
    engine2: ExecutionEngine,
    engine_id: str,
    expected_status: Status,
):
    set_execution_engine(fetcher_event, engine_id)

    no_engines_handler.handle_event(fetcher_event, kafka_service)

    kafka_service.send_status_message_event.assert_not_called()
    kafka_service.send_event.assert_not_called()
    engine1.run.assert_not_called()
    engine2.run.assert_not_called()


def test_handle_event(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    expected_executor_event: ExecutorBenchmarkEvent,
    expected_pending_call,
):
    executor_handler.handle_event(fetcher_event, kafka_service)

    kafka_service.send_status_message_event.assert_has_calls(
        [expected_pending_call, call(expected_executor_event, Status.SUCCEEDED, ANY)]
    )
    kafka_service.send_event.assert_called_once_with(expected_executor_event, PRODUCER_TOPIC)


def test_handle_event_processes_single_run_benchmark(
    executor_handler: ExecutorEventHandler,
    single_run_fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    expected_executor_event: ExecutorBenchmarkEvent,
    expected_pending_call,
):
    executor_handler.handle_event(single_run_fetcher_event, kafka_service)

    kafka_service.send_status_message_event.assert_has_calls(
        [expected_pending_call, call(expected_executor_event, Status.SUCCEEDED, ANY)]
    )
    kafka_service.send_event.assert_called_once_with(expected_executor_event, PRODUCER_TOPIC)


def test_handle_event_ignores_scheduled_events(
    executor_handler: ExecutorEventHandler,
    scheduled_run_fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
):
    executor_handler.handle_event(scheduled_run_fetcher_event, kafka_service)

    kafka_service.send_event.assert_not_called()
    kafka_service.send_status_message_event.assert_not_called()


def test_run_raises(
    executor_handler: ExecutorEventHandler,
    fetcher_event: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    engine1: ExecutionEngine,
    expected_pending_call,
):
    engine1.run.side_effect = ExecutionEngineException("Oops")

    with pytest.raises(KafkaServiceCallbackException):
        executor_handler.handle_event(fetcher_event, kafka_service)

    kafka_service.send_status_message_event.assert_has_calls(
        [expected_pending_call, call(fetcher_event, Status.ERROR, ANY)]
    )
    kafka_service.send_event.assert_not_called()
