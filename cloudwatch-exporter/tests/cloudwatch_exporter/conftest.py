from unittest.mock import MagicMock

import pytest
from bai_kafka_utils.events import MetricsEvent

from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig


@pytest.fixture
def mock_kafka_service():
    return MagicMock(spec=KafkaService)


@pytest.fixture
def metrics_event():
    return MetricsEvent(
        name="METRIC",
        value=0,
        timestamp=1576244976000,
        labels={"LABEL": "VALUE", "task_name": "test_task", "dashboard-name": "test_dashboard"},
    )


@pytest.fixture
def kafka_service_config():
    return KafkaServiceConfig(
        bootstrap_servers=["kafka1:9092", "kafka2:9092"],
        consumer_group_id="GROUP_ID",
        consumer_topic="CONSUMER_TOPIC",
        logging_level="DEBUG",
        producer_topic="OUT_TOPIC",
        status_topic="STATUS_TOPIC",
        cmd_return_topic="CMD_RETURN",
    )
