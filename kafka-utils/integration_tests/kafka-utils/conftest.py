import pytest
import os

from bai_kafka_utils.kafka_service import KafkaServiceConfig


BOOTSTRAP_SERVERS = [os.environ["KAFKA_BOOTSTRAP_SERVERS"]]


@pytest.fixture
def kafka_service_config():
    return KafkaServiceConfig(
        consumer_group_id="CONSUMER_GROUP_ID",
        producer_topic="BAI_APP_FETCHER",
        consumer_topic="BAI_APP_EXECUTOR",
        bootstrap_servers=BOOTSTRAP_SERVERS,
        logging_level="INFO",
        cmd_submit_topic="CMD_SUBMIT",
        cmd_return_topic="CMD_RETURN",
        status_topic="BAI_APP_STATUS",
    )
