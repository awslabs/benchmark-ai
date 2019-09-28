from typing import List, Type
from unittest import mock
from unittest.mock import patch, call, ANY, create_autospec

import kafka
import pytest
from bai_kafka_utils.events import (
    BenchmarkDoc,
    BenchmarkEvent,
    FetcherPayload,
    DownloadableContent,
    FetcherBenchmarkEvent,
    Status,
    FetcherStatus,
    CommandRequestEvent,
    CommandRequestPayload,
)
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig
from bai_zk_utils.zk_locker import DistributedRWLockManager
from kazoo.client import KazooClient
from pytest import fixture

from fetcher_dispatcher import fetcher_dispatcher_service, SERVICE_NAME
from fetcher_dispatcher.args import FetcherServiceConfig, FetcherJobConfig
from fetcher_dispatcher.data_set_manager import DataSetManager
from fetcher_dispatcher.fetcher_dispatcher_service import (
    create_data_set_manager,
    FetcherEventHandler,
    create_fetcher_dispatcher,
    DataSetCmdObject,
)
from fetcher_dispatcher.kubernetes_dispatcher import KubernetesDispatcher

STATUS_TOPIC = "STATUS_TOPIC"

FETCHER_JOB_IMAGE = "job/image"

ZOOKEEPER_ENSEMBLE_HOSTS = "Z1"

LOGGING_LEVEL = "INFO"

BOOTSTRAP_SERVERS = ["K1"]

PRODUCER_TOPIC = "OUT_TOPIC"

CONSUMER_TOPIC = "IN_TOPIC"

CMD_RETURN_TOPIC = "CMD_RETURN"

CMD_REQUEST_TOPIC = "CMD_REQUEST"

POD_NAME = "POD_NAME"

S3_BUCKET = "some_bucket"

KUBECONFIG = "path/cfg"

NAMESPACE = "namespace"

FETCHER_JOB_CONFIG = FetcherJobConfig(image=FETCHER_JOB_IMAGE, namespace=NAMESPACE)

TARGET_ACTION_ID = "TARGET_ACTION_ID"


@fixture
def data_set_manager() -> DataSetManager:
    return create_autospec(DataSetManager)


@fixture
def kafka_service(mocker) -> KafkaService:
    from kafka import KafkaConsumer, KafkaProducer

    kafka_service = KafkaService(
        name="kafka-service",
        version="1.0",
        callbacks={},
        kafka_consumer=mocker.create_autospec(KafkaConsumer),
        kafka_producer=mocker.create_autospec(KafkaProducer),
        pod_name=POD_NAME,
        status_topic=STATUS_TOPIC,
    )
    mocker.spy(kafka_service, "send_status_message_event")
    mocker.spy(kafka_service, "send_event")
    return kafka_service


@fixture
def benchmark_doc() -> BenchmarkDoc:
    return BenchmarkDoc({"var": "val"}, "var = val", sha1="123")


@fixture
def datasets():
    return [DownloadableContent(src="src1"), DownloadableContent(src="src2")]


@fixture
def benchmark_event_with_datasets(benchmark_doc: BenchmarkDoc, datasets) -> BenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, datasets=datasets)
    return get_benchmark_event(payload)


@fixture
def benchmark_event_without_datasets(benchmark_doc: BenchmarkDoc) -> BenchmarkEvent:
    payload = FetcherPayload(toml=benchmark_doc, datasets=[])
    return get_benchmark_event(payload)


@fixture
def fetcher_callback(data_set_manager) -> FetcherEventHandler:
    return FetcherEventHandler(PRODUCER_TOPIC, data_set_manager, S3_BUCKET)


@fixture
def command_request_payload():
    return CommandRequestPayload(command="cancel", args={"target_action_id": TARGET_ACTION_ID, "cascade": False})


@pytest.fixture
def command_request_event(command_request_payload: CommandRequestPayload):
    return CommandRequestEvent(
        action_id="ACTION_ID",
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="CLIENT_VERSION",
        client_username="CLIENT_USER",
        authenticated=False,
        tstamp=42,
        visited=[],
        type=CMD_REQUEST_TOPIC,
        payload=command_request_payload,
    )


def get_benchmark_event(payload: FetcherPayload):
    return FetcherBenchmarkEvent(
        action_id="ACTION_ID",
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="CLIENT_VERSION",
        client_username="CLIENT_USER",
        authenticated=False,
        tstamp=42,
        visited=[],
        type=PRODUCER_TOPIC,
        payload=payload,
    )


def collect_send_event_calls(kafka_service: KafkaService, cls: Type[BenchmarkEvent]) -> List[mock._Call]:
    calls = []
    for send_event_call in kafka_service.send_event.call_args_list:
        args, kwargs = send_event_call
        if isinstance(args[0], cls):
            calls.append(send_event_call)
    return calls


@pytest.mark.parametrize(
    ["fetch_status", "expected_total_status"],
    [
        (FetcherStatus.DONE, Status.PENDING),
        (FetcherStatus.CANCELED, Status.CANCELED),
        (FetcherStatus.FAILED, Status.FAILED),
    ],
)
def test_fetcher_event_handler_fetch(
    fetcher_callback: FetcherEventHandler,
    data_set_manager: DataSetManager,
    benchmark_event_with_datasets: FetcherBenchmarkEvent,
    kafka_service: KafkaService,
    datasets: List[DownloadableContent],
    fetch_status: FetcherStatus,
    expected_total_status: Status,
):
    fetcher_callback.handle_event(benchmark_event_with_datasets, kafka_service)

    # All datasets fetched
    assert data_set_manager.fetch.call_count == len(benchmark_event_with_datasets.payload.datasets)
    # Nothing yet fetched, but sent for fetching
    validate_sent_events(kafka_service, [])

    expected_sent_statuses_before = [call(ANY, Status.PENDING, "Initiating dataset download...")] + [
        call(ANY, Status.PENDING, f"Dataset {d.src} sent to fetch") for d in datasets
    ]

    validate_send_status_message_calls(kafka_service, expected_sent_statuses_before)

    validate_populated_dst(benchmark_event_with_datasets)

    simulate_fetched_datasets(data_set_manager, fetch_status)

    # Validate the event was sent downstream
    expected_sent_events = (
        [call(benchmark_event_with_datasets, PRODUCER_TOPIC)] if fetch_status == FetcherStatus.DONE else []
    )
    validate_sent_events(kafka_service, expected_sent_events)

    expected_sent_statuses_after = [call(ANY, expected_total_status, ANY) for d in datasets]
    if fetch_status == FetcherStatus.DONE:
        expected_sent_statuses_after.append(call(ANY, Status.SUCCEEDED, "All data sets processed"))
    elif fetch_status == FetcherStatus.FAILED:
        expected_sent_statuses_after.append(call(ANY, Status.FAILED, "Aborting execution"))
    elif fetch_status == FetcherStatus.CANCELED:
        expected_sent_statuses_after.append(call(ANY, Status.CANCELED, "Aborting execution"))
    validate_send_status_message_calls(kafka_service, expected_sent_statuses_before + expected_sent_statuses_after)


def validate_sent_events(kafka_service, expected_sent_events):
    assert collect_send_event_calls(kafka_service, FetcherBenchmarkEvent) == expected_sent_events


def validate_send_status_message_calls(kafka_service, expected_sent_statuses_before):
    send_status_message_calls = kafka_service.send_status_message_event.call_args_list
    assert send_status_message_calls == expected_sent_statuses_before


def test_fetcher_event_handler_nothing_to_do(
    fetcher_callback: FetcherEventHandler, benchmark_event_without_datasets: BenchmarkEvent, kafka_service: KafkaService
):
    fetcher_callback.handle_event(benchmark_event_without_datasets, kafka_service)

    assert kafka_service.send_status_message_event.call_args_list == [call(ANY, Status.SUCCEEDED, "Nothing to fetch")]

    args, _ = kafka_service.send_event.call_args_list[0]
    fetcher_event, topic = args
    assert isinstance(fetcher_event, FetcherBenchmarkEvent)
    assert topic == PRODUCER_TOPIC
    assert fetcher_event.payload.datasets == []


def validate_populated_dst(benchmark_event):
    for data_set in benchmark_event.payload.datasets:
        assert data_set.dst


def simulate_fetched_datasets(data_set_manager: DataSetManager, fetch_status: FetcherStatus):
    for kall in data_set_manager.fetch.call_args_list:
        args, _ = kall
        data_set, _, on_done = args
        data_set.status = fetch_status
        on_done(data_set)


def test_fetcher_cleanup(data_set_manager: DataSetManager):
    fetcher_callback = FetcherEventHandler(PRODUCER_TOPIC, data_set_manager, S3_BUCKET)
    fetcher_callback.cleanup()
    data_set_manager.stop.assert_called_once()


@patch.object(fetcher_dispatcher_service, "create_data_set_manager", autospec=True)
@patch.object(kafka, "KafkaProducer", autospec=True)
@patch.object(kafka, "KafkaConsumer", autospec=True)
def test_create_fetcher_dispatcher(mockKafkaConsumer, mockKafkaProducer, mock_create_data_set_manager, mocker):
    mock_data_set_manager = create_autospec(DataSetManager)
    mock_create_data_set_manager.return_value = mock_data_set_manager
    mock_create_consumer_producer = mocker.patch(
        "fetcher_dispatcher.fetcher_dispatcher_service.create_kafka_consumer_producer",
        return_value=(mockKafkaConsumer, mockKafkaProducer),
        autospec=True,
    )

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

    mock_create_consumer_producer.assert_called_once()
    mock_data_set_manager.start.assert_called_once()

    assert fetcher_service


@patch.object(fetcher_dispatcher_service, "DistributedRWLockManager", autospec=True)
@patch.object(fetcher_dispatcher_service, "DataSetManager", autospec=True)
@patch.object(fetcher_dispatcher_service, "KubernetesDispatcher", autospec=True)
@patch.object(fetcher_dispatcher_service, "KazooClient", autospec=True)
def test_create_data_set_manager(
    mockKazooClient, mockKubernetesDispatcher, mockDataSetManager, mockDistributedRWLockManager
):
    mock_zk_client = create_autospec(KazooClient)
    mock_job_dispatcher = create_autospec(KubernetesDispatcher)
    mock_lock_manager = create_autospec(DistributedRWLockManager)

    mockKazooClient.return_value = mock_zk_client
    mockKubernetesDispatcher.return_value = mock_job_dispatcher
    mockDistributedRWLockManager.return_value = mock_lock_manager

    create_data_set_manager(ZOOKEEPER_ENSEMBLE_HOSTS, KUBECONFIG, FETCHER_JOB_CONFIG)

    mockKazooClient.assert_called_once_with(ZOOKEEPER_ENSEMBLE_HOSTS)
    mockKubernetesDispatcher.assert_called_once_with(
        SERVICE_NAME, KUBECONFIG, ZOOKEEPER_ENSEMBLE_HOSTS, FETCHER_JOB_CONFIG
    )
    mockDistributedRWLockManager.assert_called_once_with(mock_zk_client, ANY, ANY)

    mockDataSetManager.assert_called_once_with(mock_zk_client, mock_job_dispatcher, mock_lock_manager)


@patch.object(fetcher_dispatcher_service, "DataSetManager", autospec=True)
def test_cmd_object_successful_delete(
    mockDataSetManager: DataSetManager, kafka_service: KafkaService, command_request_event: CommandRequestEvent
):

    k8s_deletion_results = ["deleted pods", "deleted jobs"]
    num_zk_nodes_updates = 1

    mockDataSetManager.cancel.return_value = (k8s_deletion_results, num_zk_nodes_updates)
    cmd_object = DataSetCmdObject(mockDataSetManager)
    results = cmd_object.cancel(
        kafka_service,
        command_request_event,
        "CLIENT_ID",
        command_request_event.payload.args.get("target_action_id"),
        bool(command_request_event.payload.args.get("cascade")),
    )
    assert results == {
        "k8s_deletion_results": k8s_deletion_results,
        "num_zookeeper_nodes_updated": num_zk_nodes_updates,
    }
    mockDataSetManager.cancel.assert_called_once_with("CLIENT_ID", "TARGET_ACTION_ID")
    kafka_service.send_status_message_event.assert_called_once_with(
        command_request_event, Status.PENDING, "Canceling downloads...", "TARGET_ACTION_ID"
    )


@patch.object(fetcher_dispatcher_service, "DataSetManager", autospec=True)
def test_cmd_object_nothing_to_delete(
    mockDataSetManager: DataSetManager, kafka_service: KafkaService, command_request_event: CommandRequestEvent
):

    k8s_deletion_results = []
    num_zk_nodes_updates = 0

    mockDataSetManager.cancel.return_value = (k8s_deletion_results, num_zk_nodes_updates)
    cmd_object = DataSetCmdObject(mockDataSetManager)
    results = cmd_object.cancel(
        kafka_service,
        command_request_event,
        "CLIENT_ID",
        command_request_event.payload.args.get("target_action_id"),
        bool(command_request_event.payload.args.get("cascade")),
    )
    assert results == {
        "k8s_deletion_results": k8s_deletion_results,
        "num_zookeeper_nodes_updated": num_zk_nodes_updates,
    }
    mockDataSetManager.cancel.assert_called_once_with("CLIENT_ID", "TARGET_ACTION_ID")

    assert kafka_service.send_status_message_event.mock_calls == [
        mock.call(command_request_event, Status.PENDING, "Canceling downloads...", "TARGET_ACTION_ID"),
        mock.call(command_request_event, Status.SUCCEEDED, "No downloads to cancel...", "TARGET_ACTION_ID"),
    ]


@patch.object(fetcher_dispatcher_service, "DataSetManager", autospec=True)
def test_cmd_object_emits_status_and_raises(
    mockDataSetManager: DataSetManager, kafka_service: KafkaService, command_request_event: CommandRequestEvent
):
    mockDataSetManager.cancel.side_effect = Exception("oh noes, something happen...")
    cmd_object = DataSetCmdObject(mockDataSetManager)

    with pytest.raises(Exception):
        cmd_object.cancel(
            kafka_service,
            command_request_event,
            "CLIENT_ID",
            command_request_event.payload.args.get("target_action_id"),
            bool(command_request_event.payload.args.get("cascade")),
        )

    mockDataSetManager.cancel.assert_called_once_with("CLIENT_ID", "TARGET_ACTION_ID")

    assert kafka_service.send_status_message_event.mock_calls == [
        mock.call(command_request_event, Status.PENDING, "Canceling downloads...", "TARGET_ACTION_ID"),
        mock.call(command_request_event, Status.FAILED, ANY, "TARGET_ACTION_ID"),
    ]


@pytest.mark.parametrize(
    ["fetch_statuses", "expected_status"],
    [
        ([FetcherStatus.FAILED, FetcherStatus.CANCELED], Status.CANCELED),
        ([FetcherStatus.FAILED, FetcherStatus.RUNNING], Status.FAILED),
        ([FetcherStatus.RUNNING, FetcherStatus.PENDING], Status.PENDING),
        ([FetcherStatus.DONE, FetcherStatus.RUNNING], Status.RUNNING),
        ([FetcherStatus.DONE, FetcherStatus.DONE], Status.SUCCEEDED),
    ],
)
def test_collect_status(fetch_statuses, expected_status):
    assert expected_status == FetcherEventHandler._collect_status(
        [DownloadableContent(src="some/path", status=fetch_status) for fetch_status in fetch_statuses]
    )
