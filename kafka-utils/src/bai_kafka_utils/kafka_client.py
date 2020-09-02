#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import logging
from typing import List
from typing import Tuple

import kafka
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

from bai_kafka_utils.events import BenchmarkEvent, MetricsEvent
from bai_kafka_utils.events import get_topic_event_type
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from bai_kafka_utils.utils import DEFAULT_ENCODING

logger = logging.getLogger(__name__)


# Time before a consumer or producer closes if the topics it is subscribed to are idle.
# Setting to a really high number (3 years) because we don't want it to ever close.
MAX_IDLE_TIME_MS = 100000000000


class WrongBenchmarkEventTypeException(Exception):
    pass


# args from kafka
def create_kafka_consumer_producer(
    kafka_cfg: KafkaServiceConfig, service_name: str
) -> Tuple[KafkaConsumer, KafkaProducer]:
    # Each service's Kafka consumer subscribes to both the service's input topic and the cmd_submit topic
    consumer_topics = [kafka_cfg.consumer_topic, kafka_cfg.cmd_submit_topic]

    required_topics = [
        kafka_cfg.consumer_topic,
        kafka_cfg.producer_topic,
        kafka_cfg.cmd_submit_topic,
        kafka_cfg.cmd_return_topic,
        kafka_cfg.status_topic,
    ]

    create_kafka_topics(
        required_topics,
        kafka_cfg.bootstrap_servers,
        service_name,
        kafka_cfg.num_partitions,
        kafka_cfg.replication_factor,
    )

    return (
        create_kafka_consumer(kafka_cfg.bootstrap_servers, kafka_cfg.consumer_group_id, consumer_topics),
        create_kafka_producer(kafka_cfg.bootstrap_servers),
    )


def create_kafka_consumer(
    bootstrap_servers: List[str], group_id: str, topics: List[str], value_deserializer=None
) -> kafka.KafkaConsumer:
    def json_deserializer(msg_value):
        try:
            envelope = BenchmarkEvent.from_json(msg_value.decode(DEFAULT_ENCODING))
            event_type = get_topic_event_type(envelope.type)
            return event_type.from_json(msg_value.decode(DEFAULT_ENCODING))
        # Our json deserializer can raise anything - constructor can raise anything).
        # Handling JsonDecodeError and KeyError is not enough
        # For example TypeError is possible as well. So let's play safe.
        except Exception:
            logger.exception("Failed to deserialize %s", msg_value)
            return None

    # key can be None
    def key_deserializer(key: bytes):
        try:
            return key.decode(DEFAULT_ENCODING) if key is not None else None
        except UnicodeDecodeError:
            logger.exception("Failed to deserialize key %s", key)
            return None

    value_deserializer = value_deserializer if value_deserializer is not None else json_deserializer

    return kafka.KafkaConsumer(
        *topics,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        value_deserializer=value_deserializer,
        key_deserializer=key_deserializer,
        connections_max_idle_ms=MAX_IDLE_TIME_MS,
    )


def metrics_json_deserializer(msg_value):
    # JSON deserializer for metric events
    try:
        return MetricsEvent.from_json(msg_value.decode(DEFAULT_ENCODING))
    # Our json deserializer can raise anything - constructor can raise anything).
    # Handling JsonDecodeError and KeyError is not enough
    # For example TypeError is possible as well. So let's play safe.
    except Exception:
        logger.exception("Failed to deserialize %s", msg_value)
        return None


def create_kafka_producer(bootstrap_servers: List[str]) -> kafka.KafkaProducer:
    def json_serializer(msg_value):
        return msg_value.to_json().encode(DEFAULT_ENCODING)

    def key_serializer(key: str):
        return key.encode(DEFAULT_ENCODING)

    return kafka.KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=json_serializer,
        connections_max_idle_ms=MAX_IDLE_TIME_MS,
        key_serializer=key_serializer,
    )


def create_kafka_topics(
    new_topics: List[str], bootstrap_servers: List[str], service_name: str, num_partitions: int, replication_factor: int
):
    logger.info(f"Creating kafka topics {new_topics}")

    admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers, client_id=service_name)

    for topic in new_topics:
        try:
            new_topic = NewTopic(name=topic, num_partitions=num_partitions, replication_factor=replication_factor)
            admin_client.create_topics(new_topics=[new_topic])
            logger.info(f"Created kafka topic {topic}")
        except TopicAlreadyExistsError:
            logger.exception(f"Error creating topic {topic}, it already exists")
