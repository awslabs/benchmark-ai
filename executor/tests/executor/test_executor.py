from unittest.mock import MagicMock, ANY

import pytest
from bai_kafka_utils.kafka_service import KafkaService
from bai_kafka_utils.events import (
    BenchmarkPayload,
    BenchmarkEvent,
    FetcherBenchmarkEvent,
    BenchmarkDoc,
    create_from_object,
    FetcherPayload,
    Status,
)

from executor.executor import ScheduledBenchmarkExecutorEventHandler
from executor.k8s_execution_engine import K8SExecutionEngine


def single_run_benchmark():
    return {"info": {"scheduling": "single_run"}}


def scheduled_run_benchmark():
    return {"info": {"scheduling": "*/1 * * * *"}}


def create_benchmark_event(benchmark_payload):
    doc = BenchmarkDoc(contents=benchmark_payload, doc="var = val", sha1="1234454233")
    payload = BenchmarkPayload(toml=doc)
    return BenchmarkEvent(
        action_id="ACTION_ID",
        message_id="MESSAGE_ID",
        client_id="bob",
        client_version="CLIENT_VERSION",
        client_username="CLIENT_USER",
        authenticated=False,
        tstamp=42,
        visited=[],
        type="BAI_APP_BFF",
        payload=payload,
    )


@pytest.fixture
def mock_single_run_fetcher_event():
    single_run_benchmark_event = create_benchmark_event(single_run_benchmark())
    doc = single_run_benchmark_event.payload.toml
    return create_from_object(
        FetcherBenchmarkEvent, single_run_benchmark_event, payload=FetcherPayload(datasets=[], toml=doc)
    )


@pytest.fixture
def mock_scheduled_run_fetcher_event():
    scheduled_run_benchmark_event = create_benchmark_event(scheduled_run_benchmark())
    doc = scheduled_run_benchmark_event.payload.toml
    return create_from_object(
        FetcherBenchmarkEvent, scheduled_run_benchmark_event, payload=FetcherPayload(datasets=[], toml=doc)
    )


@pytest.fixture
def mock_kafka_service():
    return MagicMock(spec=KafkaService)


@pytest.fixture
def mock_k8s_engine():
    return MagicMock(spec=K8SExecutionEngine)


def test_scheduled_benchmark_executor_ignores_single_run_event(
    mock_k8s_engine, mock_single_run_fetcher_event, mock_kafka_service
):
    """
    Tests ScheduledBenchmarkExecutorEventHandler ignores single-run benchmarks
    """
    scheduled_benchmark_handler = ScheduledBenchmarkExecutorEventHandler(mock_k8s_engine)
    scheduled_benchmark_handler.handle_event(mock_single_run_fetcher_event, mock_kafka_service)

    mock_k8s_engine.schedule.assert_not_called()
    mock_kafka_service.send_status_message_event.assert_not_called()


def test_scheduled_benchmark_executor_accepts_scheduled_run_event(
    mock_k8s_engine, mock_scheduled_run_fetcher_event, mock_kafka_service
):
    """
    Tests ScheduledBenchmarkExecutorEventHandler processes scheduled benchmarks
    """
    scheduled_benchmark_handler = ScheduledBenchmarkExecutorEventHandler(mock_k8s_engine)
    scheduled_benchmark_handler.handle_event(mock_scheduled_run_fetcher_event, mock_kafka_service)

    mock_k8s_engine.schedule.assert_called_with(mock_scheduled_run_fetcher_event)
    mock_kafka_service.send_status_message_event.assert_called_with(
        mock_scheduled_run_fetcher_event, Status.SUCCEEDED, ANY
    )
