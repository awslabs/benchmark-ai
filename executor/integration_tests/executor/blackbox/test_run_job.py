from bai_k8s_utils.kubernetes_tests_client import KubernetesTestUtilsClient
from bai_kafka_utils.events import (
    BenchmarkEvent,
    create_from_object,
    FetcherBenchmarkEvent,
    BenchmarkDoc,
    FetcherPayload,
    Status,
)
from bai_kafka_utils.integration_tests.test_loop import (
    wait_for_response,
    CombinedFilter,
    get_is_status_filter,
    EventFilter,
)
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from kafka import KafkaConsumer, KafkaProducer

POD_NAMESPACE = "default"


def get_fetcher_benchmark_event(template_event: BenchmarkEvent) -> FetcherBenchmarkEvent:
    doc = BenchmarkDoc(
        {
            "ml": {"benchmark_code": "echo hello world"},
            "info": {"task_name": "test-2"},
            "hardware": {"instance_type": "local", "strategy": "single_node"},
            "env": {"docker_image": "alpine", "vars": {"FOO": "BAR", "IVAL": 42}},
        },
        "var = val",  # We don't care about the initial TOML
        "",
    )
    fetch_payload = FetcherPayload(toml=doc, datasets=[])
    return create_from_object(
        FetcherBenchmarkEvent,
        template_event,
        payload=fetch_payload,
        action_id=template_event.action_id.replace("_", "-"),
    )


def get_is_exec_filter(src_event: BenchmarkEvent, kafka_service_config: KafkaServiceConfig) -> EventFilter:
    def filter_executor_event(event: BenchmarkEvent) -> bool:
        return event.action_id == src_event.action_id and event.type == kafka_service_config.producer_topic

    return filter_executor_event


def test_exec(
    benchmark_event_dummy_payload: BenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_prepolled_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    k8s_test_client: KubernetesTestUtilsClient,
):
    event = get_fetcher_benchmark_event(benchmark_event_dummy_payload)
    kafka_producer_to_consume.send(kafka_service_config.consumer_topic, value=event, key=event.client_id)

    k8s_test_client.wait_for_pod_exists(POD_NAMESPACE, event.client_id, event.action_id)

    combined_filter = CombinedFilter(
        [
            get_is_exec_filter(event, kafka_service_config),
            get_is_status_filter(event, Status.SUCCEEDED, kafka_service_config),
        ]
    )

    wait_for_response(combined_filter, kafka_prepolled_consumer_of_produced)
