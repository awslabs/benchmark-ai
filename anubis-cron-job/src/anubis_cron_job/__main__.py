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
import dataclasses
import logging
import os
import sys

import dacite
from bai_kafka_utils.events import FetcherBenchmarkEvent, Status
from bai_kafka_utils.kafka_client import create_kafka_producer
from bai_kafka_utils.kafka_service import EventEmitter
from bai_kafka_utils.executors.descriptor import SINGLE_RUN_SCHEDULING
from bai_kafka_utils.logging import configure_logging
from bai_kafka_utils.utils import generate_uuid, get_pod_name

from anubis_cron_job import __version__, SERVICE_NAME
from anubis_cron_job.config import get_config


def create_benchmark_event(scheduled_benchmark_event: FetcherBenchmarkEvent) -> FetcherBenchmarkEvent:
    benchmark_event = dataclasses.replace(
        scheduled_benchmark_event, action_id=generate_uuid(), parent_action_id=scheduled_benchmark_event.action_id
    )

    # Set scheduling to single run
    info = benchmark_event.payload.toml.contents.get("info")
    if info:
        info["scheduling"] = SINGLE_RUN_SCHEDULING
    else:
        raise RuntimeError("Event does not contain valid benchmark descriptor: 'info' section is missing.")

    return benchmark_event


def main(argv=None):
    configure_logging(level=logging.INFO)
    logger = logging.getLogger("BAI_CRON_JOB")

    logger.info("Loading configuration")
    logger.info(os.environ)

    try:
        config = get_config(argv, os.environ)

        logging.info("Updating benchmark event's message and action id")
        scheduled_benchmark_event = dacite.from_dict(data_class=FetcherBenchmarkEvent, data=config.benchmark_event)
        benchmark_event = create_benchmark_event(scheduled_benchmark_event)

        logging.info("Creating Kafka producer")
        kafka_producer = create_kafka_producer(config.kafka_bootstrap_servers)

        event_emitter = EventEmitter(
            name=SERVICE_NAME,
            version=__version__,
            pod_name=get_pod_name(),
            status_topic=config.status_topic,
            kakfa_producer=kafka_producer,
        )

        logging.info(f"Submitting benchmark with action id {benchmark_event.action_id}")
        event_emitter.send_event(event=benchmark_event, topic=config.producer_topic)

        # Send the message against the original scheduled benchmark event so it is logged
        # against the original action_id
        event_emitter.send_status_message_event(
            handled_event=scheduled_benchmark_event,
            status=Status.SUCCEEDED,
            msg=f"Spawning benchmark with action_id: [{benchmark_event.action_id}]",
        )
        logging.debug("Closing producer")
        kafka_producer.close()
    except Exception as err:
        logger.exception(f"Fatal error submitting benchmark job: {err}")
        sys.exit(1)

    logging.info("Success")


if __name__ == "__main__":
    main(sys.argv)
