import json
import kafka
import logging
import os
import sys
import uuid

from typing import Dict

from bai_kafka_utils.kafka_client import MAX_IDLE_TIME_MS
from bai_kafka_utils.utils import DEFAULT_ENCODING

logger = logging.getLogger("BAI_CRON_JOB")

# Environment variable keys
KAFKA_BOOTSTRAP_SERVERS = "KAFKA_BOOTSTRAP_SERVERS"
PRODUCER_TOPIC = "PRODUCER_TOPIC"
BENCHMARK_EVENT = "BENCHMARK_EVENT"


def env_get_or_fail(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"No value found for environment variable {key}")
    return value


def get_cron_benchmark_event() -> Dict[str, str]:
    benchmark_event = json.loads(env_get_or_fail(BENCHMARK_EVENT))
    required_fields = ["client_id", "message_id", "action_id"]
    for required_field in required_fields:
        if not benchmark_event.get(required_field):
            raise ValueError(f"Benchmark event does not contain field {required_field}")

    return benchmark_event


def main():
    logger.info("Attempting to submit cron benchmark")
    logger.debug("Loading configuration")
    kafka_bootstrap_servers = env_get_or_fail(KAFKA_BOOTSTRAP_SERVERS).split(",")
    producer_topic = env_get_or_fail(PRODUCER_TOPIC)
    benchmark_event = get_cron_benchmark_event()

    logging.info("Updating benchmark event's message and action id")
    benchmark_event["message_id"] = str(uuid.uuid4())
    benchmark_event["action_id"] = str(uuid.uuid4())

    logging.info("Creating Kafka producer")
    kafka_producer = kafka.KafkaProducer(
        bootstrap_servers=kafka_bootstrap_servers,
        value_serializer=lambda x: json.dumps(x).encode(DEFAULT_ENCODING),
        connections_max_idle_ms=MAX_IDLE_TIME_MS,
        key_serializer=lambda x: x.encode(DEFAULT_ENCODING),
    )

    logging.info("Submitting benchmark")
    kafka_producer.send(producer_topic, value=benchmark_event, key=benchmark_event["client_id"])

    logging.debug("Closing producer")
    kafka_producer.close()

    logging.info("Success")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        logger.error(f"Fatal error submitting benchmark job: {err}")
        sys.exit(1)
    sys.exit(0)
