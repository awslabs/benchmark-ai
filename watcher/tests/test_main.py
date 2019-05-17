from unittest.mock import Mock

from bai_watcher.args import WatcherServiceConfig
from bai_kafka_utils.kafka_service import KafkaServiceConfig


BOOTSTRAP_SERVERS = ["K1", "K2"]
LOGGING_LEVEL = "WARN"
CONSUMER_TOPIC = "IN"
PRODUCER_TOPIC = "OUT"
STATUS_TOPIC = "STATUS_TOPIC"
BOOTSTRAP_SERVERS_ARG = ",".join(BOOTSTRAP_SERVERS)


def test_main(mocker):
    mock_create_service = mocker.patch("bai_watcher.kafka_service_watcher.create_service")
    mock_watcher_service = Mock()
    mock_create_service.return_value = mock_watcher_service
    from bai_watcher.__main__ import main

    main(
        f" --consumer-topic {CONSUMER_TOPIC} "
        f" --producer-topic {PRODUCER_TOPIC} "
        f" --status-topic {STATUS_TOPIC} "
        f" --bootstrap-servers {BOOTSTRAP_SERVERS_ARG} "
        f" --logging-level {LOGGING_LEVEL} "
        f" --kubeconfig kubeconfig "
        f" --kubernetes-namespace-of-running-jobs kubernetes-namespace "
    )

    expected_common_kafka_cfg = KafkaServiceConfig(
        consumer_topic=CONSUMER_TOPIC,
        producer_topic=PRODUCER_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        logging_level=LOGGING_LEVEL,
        status_topic=STATUS_TOPIC,
    )

    expected_watcher_config = WatcherServiceConfig(
        kubernetes_namespace_of_running_jobs="kubernetes-namespace", kubeconfig="kubeconfig"
    )

    mock_create_service.assert_called_with(expected_common_kafka_cfg, expected_watcher_config)
    mock_watcher_service.run_loop.assert_called_once()
