import dacite
import json
import logging
import os
import sys
from typing import Dict

from bai_kafka_utils.events import FetcherBenchmarkEvent
from bai_kafka_utils.kafka_client import create_kafka_producer
from bai_kafka_utils.utils import generate_uuid

from bai_cron_job.args import get_args

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


def main(argv=None):
    logger.info(f"Loading configuration {argv} {os.environ}")
    args = get_args(argv, os.environ)

    logging.info("Updating benchmark event's message and action id")
    benchmark_event = dacite.from_dict(data_class=FetcherBenchmarkEvent, data=args.benchmark_event)

    benchmark_event.message_id = generate_uuid()
    benchmark_event.action_id = generate_uuid()

    # Remove scheduling attribute from toml
    info = benchmark_event.payload.toml.contents.get("info", {})
    if "scheduling" in info:
        info.pop("scheduling")

    logging.info("Creating Kafka producer")
    kafka_producer = create_kafka_producer(args.kafka_bootstrap_servers)

    logging.info("Submitting benchmark")
    kafka_producer.send(args.producer_topic, value=benchmark_event, key=benchmark_event["client_id"])

    logging.debug("Closing producer")
    kafka_producer.close()

    logging.info("Success")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception as err:
        logger.error(f"Fatal error submitting benchmark job: {err}")
        sys.exit(1)
    sys.exit(0)
