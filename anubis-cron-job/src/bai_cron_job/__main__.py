import logging
import os
import sys

import dacite
from bai_kafka_utils.events import FetcherBenchmarkEvent
from bai_kafka_utils.kafka_client import create_kafka_producer
from bai_kafka_utils.logging import configure_logging
from bai_kafka_utils.utils import generate_uuid

from bai_cron_job.args import get_args


def main(argv=None):
    configure_logging(level=logging.INFO)
    logger = logging.getLogger("BAI_CRON_JOB")

    logger.info("Loading configuration")
    logger.info(os.environ)

    try:
        args = get_args(argv, os.environ)

        logging.info("Updating benchmark event's message and action id")
        benchmark_event = dacite.from_dict(data_class=FetcherBenchmarkEvent, data=args.benchmark_event)

        # Create new message and action ids
        benchmark_event.message_id = generate_uuid()
        benchmark_event.action_id = generate_uuid()

        # Remove scheduling attribute from toml
        info = benchmark_event.payload.toml.contents.get("info", {})
        if "scheduling" in info:
            info.pop("scheduling")

        logging.info("Creating Kafka producer")
        kafka_producer = create_kafka_producer(args.kafka_bootstrap_servers)

        logging.info(f"Submitting benchmark with action id {benchmark_event.action_id}")
        kafka_producer.send(args.producer_topic, value=benchmark_event, key=benchmark_event.client_id)

        logging.debug("Closing producer")
        kafka_producer.close()
    except Exception as err:
        logger.error(f"Fatal error submitting benchmark job: {err}")
        sys.exit(1)

    logging.info("Success")


if __name__ == "__main__":
    main(sys.argv)
