import kafka
from kazoo.client import KazooClient

from fetcher_dispatcher.fetcher_dispatcher import (
    create_data_set_manager,
    FetcherEventHandler,
    create_fetcher_dispatcher,
)
from fetcher_dispatcher.kubernetes_client import KubernetesDispatcher
from pytest import fixture
from unittest.mock import MagicMock, patch

from bai_kafka_utils.events import BenchmarkDoc, BenchmarkEvent, FetcherPayload, DataSet
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig
from fetcher_dispatcher import fetcher_dispatcher
from fetcher_dispatcher.args import FetcherServiceConfig, FetcherJobConfig
from fetcher_dispatcher.data_set_manager import DataSetManager


FETCHER_JOB_IMAGE = "job/image"

ZOOKEEPER_ENSEMBLE_HOSTS = "Z1"

LOGGING_LEVEL = "INFO"

BOOTSTRAP_SERVERS = ["K1"]

PRODUCER_TOPIC = "OUT_TOPIC"

CONSUMER_TOPIC = "IN_TOPIC"

S3_BUCKET = "some_bucket"

KUBECONFIG = "path/cfg"

NAMESPACE = "namespace"

FETCHER_JOB_CONFIG = FetcherJobConfig(image=FETCHER_JOB_IMAGE, namespace=NAMESPACE)


@fixture
def data_set_manager() -> DataSetManager:
    return MagicMock(spec=DataSetManager)


@fixture
def kafka_service() -> KafkaService:
    return MagicMock(spec=KafkaService)


@fixture
def benchmark_doc() -> BenchmarkDoc:
    return BenchmarkDoc({"var": "val"}, "var = val", sha1="123")


@fixture
def benchmark_event_with_datasets(benchmark_doc: BenchmarkDoc) -> BenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, datasets=[DataSet(src="src1"), DataSet(src="src2")])
    return get_benchmark_event(payload)


@fixture
def benchmark_event_without_datasets(benchmark_doc: BenchmarkDoc) -> BenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, datasets=[])
    return get_benchmark_event(payload)


def get_benchmark_event(payload):
    return BenchmarkEvent(
        action_id="ACTION_ID",
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="CLIENT_VERSION",
        client_username="CLIENT_USER",
        authenticated=False,
        tstamp=42,
        visited=[],
        payload=payload,
    )


def test_fetcher_event_handler_fetch(
    data_set_manager: DataSetManager, benchmark_event_with_datasets: BenchmarkEvent, kafka_service: KafkaService
):
    fetcher_callback = FetcherEventHandler(data_set_manager, S3_BUCKET)
    event_to_send_sync = fetcher_callback.handle_event(benchmark_event_with_datasets, kafka_service)

    # Nothing to send immediately
    assert not event_to_send_sync
    # All datasets fetched
    assert data_set_manager.fetch.call_count == len(benchmark_event_with_datasets.payload.datasets)
    # Nothing yet sent
    kafka_service.send_event.assert_not_called()

    validate_populated_dst(benchmark_event_with_datasets)

    simulate_fetched_datasets(data_set_manager)

    kafka_service.send_event.assert_called_once()


def test_fetcher_event_handler_nothing_to_do(
    data_set_manager: DataSetManager, benchmark_event_without_datasets: BenchmarkEvent, kafka_service: KafkaService
):
    fetcher_callback = FetcherEventHandler(data_set_manager, S3_BUCKET)
    event_to_send_sync = fetcher_callback.handle_event(benchmark_event_without_datasets, kafka_service)
    assert event_to_send_sync == benchmark_event_without_datasets


def validate_populated_dst(benchmark_event):
    for data_set in benchmark_event.payload.datasets:
        assert data_set.dst


def simulate_fetched_datasets(data_set_manager):
    for call in data_set_manager.fetch.call_args_list:
        args = call[0]
        data_set = args[0]
        on_done = args[1]
        on_done(data_set)


def test_fetcher_cleanup(data_set_manager: DataSetManager):
    fetcher_callback = FetcherEventHandler(data_set_manager, S3_BUCKET)
    fetcher_callback.cleanup()
    data_set_manager.stop.assert_called_once()


@patch.object(fetcher_dispatcher, "create_data_set_manager")
@patch.object(kafka, "KafkaProducer")
@patch.object(kafka, "KafkaConsumer")
def test_create_fetcher_dispatcher(mockKafkaConsumer, mockKafkaProducer, mock_create_data_set_manager):

    mock_data_set_manager = MagicMock(spec=DataSetManager)
    mock_create_data_set_manager.return_value = mock_data_set_manager

    common_cfg = KafkaServiceConfig(
        consumer_topic=CONSUMER_TOPIC,
        producer_topic=PRODUCER_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        logging_level=LOGGING_LEVEL,
    )
    fetcher_cfg = FetcherServiceConfig(
        zookeeper_ensemble_hosts=ZOOKEEPER_ENSEMBLE_HOSTS,
        s3_data_set_bucket=S3_BUCKET,
        fetcher_job=FetcherJobConfig(image=FETCHER_JOB_IMAGE, namespace=NAMESPACE),
    )
    fetcher_service = create_fetcher_dispatcher(common_cfg, fetcher_cfg)

    mockKafkaConsumer.assert_called_once()
    mockKafkaProducer.assert_called_once()

    mock_data_set_manager.start.assert_called_once()

    assert fetcher_service


@patch.object(fetcher_dispatcher, "DataSetManager")
@patch.object(fetcher_dispatcher, "KubernetesDispatcher")
@patch.object(fetcher_dispatcher, "KazooClient")
def test_create_data_set_manager(mockKazooClient, mockKubernetesDispatcher, mockDataSetManager):
    mock_zk_client = MagicMock(spec=KazooClient)
    mock_job_dispatcher = MagicMock(spec=KubernetesDispatcher)

    mockKazooClient.return_value = mock_zk_client
    mockKubernetesDispatcher.return_value = mock_job_dispatcher

    create_data_set_manager(ZOOKEEPER_ENSEMBLE_HOSTS, KUBECONFIG, FETCHER_JOB_CONFIG)

    mockKazooClient.assert_called_with(ZOOKEEPER_ENSEMBLE_HOSTS)
    mockKubernetesDispatcher.assert_called_with(KUBECONFIG, ZOOKEEPER_ENSEMBLE_HOSTS, FETCHER_JOB_CONFIG)

    mockDataSetManager.assert_called_with(mock_zk_client, mock_job_dispatcher)
