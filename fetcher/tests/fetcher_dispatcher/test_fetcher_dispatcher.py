from pytest import fixture
from unittest.mock import MagicMock

from bai_kafka_utils.events import BenchmarkDoc, BenchmarkEvent, FetcherPayload, DataSet
from bai_kafka_utils.kafka_service import KafkaService
from fetcher_dispatcher.data_set_manager import DataSetManager
from fetcher_dispatcher.fetcher_dispatcher import FetcherEventHandler

S3_BUCKET = "some_bucket"


@fixture
def data_set_manager() -> DataSetManager:
    return MagicMock(spec=DataSetManager)


@fixture
def kafka_service() -> KafkaService:
    return MagicMock(spec=KafkaService)


@fixture
def benchmark_doc() -> BenchmarkDoc:
    return BenchmarkDoc({"var": "val"}, "var = val", md5="123")


@fixture
def benchmark_event_with_data_sets(benchmark_doc: BenchmarkDoc) -> BenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, data_sets=[DataSet(src="src1"), DataSet(src="src2")])
    return get_benchmark_event(payload)


@fixture
def benchmark_event_without_data_sets(benchmark_doc: BenchmarkDoc) -> BenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, data_sets=[])
    return get_benchmark_event(payload)


def get_benchmark_event(payload):
    return BenchmarkEvent(request_id="REQUEST_ID", message_id="MESSAGE_ID", client_id="CLIENT_ID",
                          client_version="CLIENT_VERSION", client_user="CLIENT_USER", authenticated=False,
                          date=42, visited=[],
                          payload=payload)


def test_fetcher_event_handler_fetch(data_set_manager: DataSetManager, benchmark_event_with_data_sets: BenchmarkEvent,
                                     kafka_service: KafkaService):
    fetcher_callback = FetcherEventHandler(data_set_manager, S3_BUCKET)
    event_to_send_sync = fetcher_callback.handle_event(benchmark_event_with_data_sets, kafka_service)

    # Nothing to send immediately
    assert not event_to_send_sync
    # All data_sets fetched
    assert data_set_manager.fetch.call_count == len(benchmark_event_with_data_sets.payload.data_sets)
    # Nothing yet sent
    kafka_service.send_event.assert_not_called()

    validate_populated_dst(benchmark_event_with_data_sets)

    simulate_fetched_data_sets(data_set_manager)

    kafka_service.send_event.assert_called_once()


def test_fetcher_event_handler_nothing_to_do(data_set_manager: DataSetManager,
                                             benchmark_event_without_data_sets: BenchmarkEvent,
                                             kafka_service: KafkaService):
    fetcher_callback = FetcherEventHandler(data_set_manager, S3_BUCKET)
    event_to_send_sync = fetcher_callback.handle_event(benchmark_event_without_data_sets, kafka_service)
    assert event_to_send_sync == benchmark_event_without_data_sets


def validate_populated_dst(benchmark_event):
    for data_set in benchmark_event.payload.data_sets:
        assert data_set.dst


def simulate_fetched_data_sets(data_set_manager):
    for call in data_set_manager.fetch.call_args_list:
        args = call[0]
        data_set = args[0]
        on_done = args[1]
        on_done(data_set)


def test_fetcher_cleanup(data_set_manager: DataSetManager):
    fetcher_callback = FetcherEventHandler(data_set_manager, S3_BUCKET)
    fetcher_callback.cleanup()
    data_set_manager.stop.assert_called_once()
