from bai_k8s_utils.kubernetes_tests_client import KubernetesTestUtilsClient
from bai_kafka_utils.cmd_callback import KafkaCommandCallback
from bai_kafka_utils.events import BenchmarkEvent, FetcherBenchmarkEvent, Status
from bai_kafka_utils.integration_tests.test_loop import (
    wait_for_response,
    CombinedFilter,
    get_is_status_filter,
    EventFilter,
    get_cancel_event,
    get_is_command_return_filter,
)
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from kafka import KafkaConsumer, KafkaProducer

POD_NAMESPACE = "default"


def get_is_exec_filter(src_event: BenchmarkEvent, kafka_service_config: KafkaServiceConfig) -> EventFilter:
    def filter_executor_event(event: BenchmarkEvent) -> bool:
        return event.action_id == src_event.action_id and event.type == kafka_service_config.producer_topic

    return filter_executor_event


def get_is_parent_exec_filter(src_event: BenchmarkEvent, kafka_service_config: KafkaServiceConfig) -> EventFilter:
    def filter_executor_event(event: BenchmarkEvent) -> bool:
        return event.parent_action_id == src_event.action_id and event.type == kafka_service_config.producer_topic

    return filter_executor_event


def test_cron_job_exec(
    fetcher_benchmark_event: FetcherBenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_prepolled_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    k8s_test_client: KubernetesTestUtilsClient,
):

    # Create scheduled benchmark
    fetcher_benchmark_event.payload.toml.contents["info"]["scheduling"] = "*/1 * * * *"

    kafka_producer_to_consume.send(
        kafka_service_config.consumer_topic, value=fetcher_benchmark_event, key=fetcher_benchmark_event.client_id
    )

    k8s_test_client.wait_for_cron_job_exists(
        POD_NAMESPACE, fetcher_benchmark_event.client_id, fetcher_benchmark_event.action_id
    )

    combined_filter = CombinedFilter(
        [
            get_is_parent_exec_filter(fetcher_benchmark_event, kafka_service_config),
            get_is_status_filter(fetcher_benchmark_event, Status.SUCCEEDED, kafka_service_config),
        ]
    )

    try:
        wait_for_response(combined_filter, kafka_prepolled_consumer_of_produced, duration=300)
    finally:
        cancel_event = get_cancel_event(fetcher_benchmark_event, kafka_service_config.cmd_submit_topic, cascade=True)
        kafka_producer_to_consume.send(
            kafka_service_config.cmd_submit_topic, value=cancel_event, key=cancel_event.client_id
        )
        command_return_filter = get_is_command_return_filter(
            cancel_event, KafkaCommandCallback.CODE_SUCCESS, kafka_service_config
        )

        wait_for_response(command_return_filter, kafka_prepolled_consumer_of_produced)
