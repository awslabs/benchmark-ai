import logging

from typing import List
from kafka import KafkaConsumer
from bai_kafka_utils.kafka_client import create_kafka_topics

logger = logging.getLogger(__name__)

TOPIC_NAME = "TOPIC_1"
OTHER_TOPIC_NAME = "TOPIC_2"
SERVICE_NAME = "TEST_KAFKA_CLIENT"


def list_topics(bootstrap_servers: List[str]):
    consumer = KafkaConsumer(group_id="GROUP_ID", bootstrap_servers=bootstrap_servers)
    topics = consumer.topics()
    consumer.close()
    return topics


# Utility function to have unique topic names per test
def add_prefix(topic_name: str, test_number: int):
    return f"TEST{test_number}_{topic_name}"


def test_create_new_topic(kafka_service_config):
    topic_name = add_prefix(TOPIC_NAME, 1)

    create_kafka_topics(
        new_topics=[topic_name],
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )
    topics = list_topics(kafka_service_config.bootstrap_servers)

    assert topic_name in topics


def test_create_multiple_topics(kafka_service_config):
    topics_to_create = [add_prefix(topic, 2) for topic in [TOPIC_NAME, OTHER_TOPIC_NAME]]

    create_kafka_topics(
        new_topics=topics_to_create,
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )

    topics = list_topics(kafka_service_config.bootstrap_servers)
    for t in topics_to_create:
        assert t in topics


def test_create_existing_topic(kafka_service_config):
    topic_name = add_prefix(TOPIC_NAME, 3)

    # Create the topic twice
    for _ in range(2):
        create_kafka_topics(
            new_topics=[topic_name],
            bootstrap_servers=kafka_service_config.bootstrap_servers,
            service_name=SERVICE_NAME,
            replication_factor=1,
            num_partitions=1,
        )

        topics = list_topics(kafka_service_config.bootstrap_servers)
        assert topic_name in topics


def test_create_multiple_topics_one_existing(kafka_service_config):
    topics_to_create = [add_prefix(topic, 4) for topic in [TOPIC_NAME, OTHER_TOPIC_NAME]]

    create_kafka_topics(
        new_topics=[topics_to_create[0]],
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )

    topics = list_topics(kafka_service_config.bootstrap_servers)
    assert topics_to_create[0] in topics

    create_kafka_topics(
        new_topics=topics_to_create,
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )

    topics = list_topics(kafka_service_config.bootstrap_servers)
    assert topics_to_create[1] in topics
