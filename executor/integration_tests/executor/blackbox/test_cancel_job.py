from bai_k8s_utils.kubernetes_tests_client import KubernetesTestUtilsClient
from bai_kafka_utils.cmd_callback import KafkaCommandCallback
from bai_kafka_utils.events import FetcherBenchmarkEvent
from bai_kafka_utils.integration_tests.test_loop import (
    wait_for_response,
    get_is_command_return_filter,
    get_cancel_event,
)
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from kafka import KafkaConsumer, KafkaProducer

POD_NAMESPACE = "default"


def test_cancel(
    fetcher_benchmark_event: FetcherBenchmarkEvent,
    kafka_producer_to_consume: KafkaProducer,
    kafka_prepolled_consumer_of_produced: KafkaConsumer,
    kafka_service_config: KafkaServiceConfig,
    k8s_test_client: KubernetesTestUtilsClient,
):
    fetcher_benchmark_event.payload.toml.contents["ml"]["benchmark_code"] = "sleep 60s"

    kafka_producer_to_consume.send(
        kafka_service_config.consumer_topic, value=fetcher_benchmark_event, key=fetcher_benchmark_event.client_id
    )

    k8s_test_client.wait_for_pod_exists(
        POD_NAMESPACE, fetcher_benchmark_event.client_id, fetcher_benchmark_event.action_id
    )

    cancel_event = get_cancel_event(fetcher_benchmark_event, kafka_service_config.cmd_submit_topic)
    kafka_producer_to_consume.send(
        kafka_service_config.cmd_submit_topic, value=cancel_event, key=cancel_event.client_id
    )
    command_return_filter = get_is_command_return_filter(
        cancel_event, KafkaCommandCallback.CODE_SUCCESS, kafka_service_config
    )

    wait_for_response(command_return_filter, kafka_prepolled_consumer_of_produced)

    k8s_test_client.wait_for_pod_not_exists(
        POD_NAMESPACE, fetcher_benchmark_event.client_id, fetcher_benchmark_event.action_id
    )
