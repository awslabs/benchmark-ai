import logging

from typing import List
from kafka import KafkaConsumer, KafkaAdminClient
from bai_kafka_utils.kafka_client import create_kafka_topics

logger = logging.getLogger(__name__)

TOPIC_NAME = "TEST_TOPIC_1"
OTHER_TOPIC_NAME = "TEST_TOPIC_2"
SERVICE_NAME = "TEST_KAFKA_CLIENT"


def list_topics(bootstrap_servers: List[str]):
    consumer = KafkaConsumer(group_id="GROUP_ID", bootstrap_servers=bootstrap_servers)
    topics = consumer.topics()
    consumer.close()
    return topics


def delete_topics(topics: List[str], bootstrap_servers: List[str]):
    logging.info(f"Existing topics: {list_topics(bootstrap_servers)}")
    logging.info(f"Deleting topics {topics}")
    admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers, client_id=SERVICE_NAME)
    admin_client.delete_topics(topics)
    admin_client.close()
    logging.info(f"Remaining topics: {list_topics(bootstrap_servers)}")


def test_create_new_topic(kafka_service_config):
    create_kafka_topics(
        new_topics=[TOPIC_NAME],
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )
    topics = list_topics(kafka_service_config.bootstrap_servers)

    assert TOPIC_NAME in topics

    delete_topics([TOPIC_NAME], kafka_service_config.bootstrap_servers)


def test_create_multiple_topics(kafka_service_config):
    topics_to_create = [TOPIC_NAME, OTHER_TOPIC_NAME]
    create_kafka_topics(
        new_topics=topics_to_create,
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )

    topics = list_topics(kafka_service_config.bootstrap_servers)
    assert TOPIC_NAME in topics
    assert OTHER_TOPIC_NAME in topics

    delete_topics(topics_to_create, kafka_service_config.bootstrap_servers)


def test_create_existing_topic(kafka_service_config):
    create_kafka_topics(
        new_topics=[TOPIC_NAME],
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )

    topics = list_topics(kafka_service_config.bootstrap_servers)
    assert TOPIC_NAME in topics

    create_kafka_topics(
        new_topics=[TOPIC_NAME],
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )

    topics = list_topics(kafka_service_config.bootstrap_servers)
    assert TOPIC_NAME in topics

    delete_topics([TOPIC_NAME], kafka_service_config.bootstrap_servers)


def test_create_multiple_topics_one_existing(kafka_service_config):
    create_kafka_topics(
        new_topics=[TOPIC_NAME],
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )

    topics = list_topics(kafka_service_config.bootstrap_servers)
    assert TOPIC_NAME in topics

    create_kafka_topics(
        new_topics=[TOPIC_NAME, OTHER_TOPIC_NAME],
        bootstrap_servers=kafka_service_config.bootstrap_servers,
        service_name=SERVICE_NAME,
        replication_factor=1,
        num_partitions=1,
    )

    topics = list_topics(kafka_service_config.bootstrap_servers)
    assert OTHER_TOPIC_NAME in topics

    delete_topics([TOPIC_NAME, OTHER_TOPIC_NAME], kafka_service_config.bootstrap_servers)
