import os
import tarfile

import boto3
from bai_k8s_utils.kubernetes_tests_client import KubernetesTestUtilsClient
from bai_kafka_utils.events import BenchmarkEvent, FetcherBenchmarkEvent, Status, FileSystemObject
from bai_kafka_utils.integration_tests.test_loop import (
    wait_for_response,
    CombinedFilter,
    get_is_status_filter,
    EventFilter,
)
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from io import BytesIO
from kafka import KafkaConsumer, KafkaProducer
from pytest import fixture

SCRIPTS_IMAGE = "python:3-alpine"

SCRIPTS = [FileSystemObject("s3://scripts-exchange/script.tar")]

SCRIPTS_COMMAND = "python3 $(BAI_SCRIPTS_PATH)/hello.py"

POD_NAMESPACE = "default"

SCRIPT_EXCHANGE_BUCKET = "scripts-exchange"


def get_is_exec_filter(src_event: BenchmarkEvent, kafka_service_config: KafkaServiceConfig) -> EventFilter:
    def filter_executor_event(event: BenchmarkEvent) -> bool:
        return event.action_id == src_event.action_id and event.type == kafka_service_config.producer_topic

    return filter_executor_event


@fixture
def s3():
    s3_endpoint_url = os.environ.get("S3_ENDPOINT")
    return boto3.resource("s3", endpoint_url=s3_endpoint_url)


@fixture
def tar_content():
    content_stream = BytesIO(b"print('Hello')\n")
    tar_stream = BytesIO()

    tar = tarfile.open(fileobj=tar_stream, mode="w", name="script.tar")
    tarinfo = tarfile.TarInfo("hello.py")
    tarinfo.size = len(content_stream.getvalue())
    tar.addfile(tarinfo, fileobj=content_stream)
    tar.close()
    return tar_stream.getvalue()


@fixture
def s3_with_a_script_file(s3, tar_content: bytes):
    bucket = s3.Bucket(SCRIPT_EXCHANGE_BUCKET)
    bucket.put_object(Body=tar_content, Key="script.tar")
    return s3


@fixture
def fetcher_benchmark_event_with_scripts(fetcher_benchmark_event):
    fetcher_benchmark_event.payload.scripts = SCRIPTS
    fetcher_benchmark_event.payload.toml.contents["ml"]["benchmark_code"] = SCRIPTS_COMMAND
    fetcher_benchmark_event.payload.toml.contents["env"]["docker_image"] = SCRIPTS_IMAGE
    return fetcher_benchmark_event


def test_exec(
    fetcher_benchmark_event: FetcherBenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_prepolled_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    k8s_test_client: KubernetesTestUtilsClient,
):
    _test_schedule_and_wait(
        fetcher_benchmark_event,
        kafka_producer_to_consume,
        kafka_prepolled_consumer_of_produced,
        kafka_service_config,
        k8s_test_client,
    )


def test_inference_exec(
    fetcher_inference_benchmark_event: FetcherBenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_prepolled_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    k8s_test_client: KubernetesTestUtilsClient,
):
    _inference_benchmark_schedule_wait(
        fetcher_inference_benchmark_event,
        kafka_producer_to_consume,
        kafka_prepolled_consumer_of_produced,
        kafka_service_config,
        k8s_test_client,
    )


def test_exec_with_scripts(
    fetcher_benchmark_event_with_scripts: FetcherBenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_prepolled_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    k8s_test_client: KubernetesTestUtilsClient,
    s3_with_a_script_file,
):
    _test_schedule_and_wait(
        fetcher_benchmark_event_with_scripts,
        kafka_producer_to_consume,
        kafka_prepolled_consumer_of_produced,
        kafka_service_config,
        k8s_test_client,
    )


def _test_schedule_and_wait(
    fetcher_benchmark_event: FetcherBenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_prepolled_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    k8s_test_client: KubernetesTestUtilsClient,
):
    kafka_producer_to_consume.send(
        kafka_service_config.consumer_topic, value=fetcher_benchmark_event, key=fetcher_benchmark_event.client_id
    )
    k8s_test_client.wait_for_pod_exists(
        POD_NAMESPACE, fetcher_benchmark_event.client_id, fetcher_benchmark_event.action_id
    )
    combined_filter = CombinedFilter(
        [
            get_is_exec_filter(fetcher_benchmark_event, kafka_service_config),
            get_is_status_filter(fetcher_benchmark_event, Status.SUCCEEDED, kafka_service_config),
        ]
    )
    wait_for_response(combined_filter, kafka_prepolled_consumer_of_produced)
    k8s_test_client.wait_for_pod_succeeded(
        POD_NAMESPACE, fetcher_benchmark_event.client_id, fetcher_benchmark_event.action_id
    )


def _inference_benchmark_schedule_wait(
    fetcher_benchmark_event: FetcherBenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_prepolled_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    k8s_test_client: KubernetesTestUtilsClient,
):
    kafka_producer_to_consume.send(
        kafka_service_config.consumer_topic, value=fetcher_benchmark_event, key=fetcher_benchmark_event.client_id
    )
    k8s_test_client.wait_for_inference_jobs_exists(
        POD_NAMESPACE, fetcher_benchmark_event.client_id, fetcher_benchmark_event.action_id
    )
    k8s_test_client.wait_for_service_exists(
        POD_NAMESPACE, fetcher_benchmark_event.client_id, fetcher_benchmark_event.action_id
    )
    combined_filter = CombinedFilter(
        [
            get_is_exec_filter(fetcher_benchmark_event, kafka_service_config),
            get_is_status_filter(fetcher_benchmark_event, Status.SUCCEEDED, kafka_service_config),
        ]
    )
    wait_for_response(combined_filter, kafka_prepolled_consumer_of_produced)
    k8s_test_client.wait_for_inference_benchmark_client_succeeded(
        POD_NAMESPACE, fetcher_benchmark_event.client_id, fetcher_benchmark_event.action_id
    )
