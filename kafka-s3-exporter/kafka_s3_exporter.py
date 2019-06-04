#!/usr/bin/env python3

# This script connects to Kafka, creates a consumer group, polls the server for data,
# and exports that to the BAI S3 log bucket

from kafka import KafkaConsumer
import logging
from pathlib import Path

DATA_DIR = str(Path.home()) + "/.bai"


def main():
    logging.getLogger().setLevel(logging.DEBUG)

    logging.info(DATA_DIR)


def get_kafka_config():
    logging.info("get_kafka_config")


if __name__ == "__main__":
    main()
