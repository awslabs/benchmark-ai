import logging

from bai_kafka_utils.kafka_service_args import get_kafka_service_config
from bai_kafka_utils.logging import configure_logging

from cloudwatch_exporter import SERVICE_NAME, SERVICE_DESCRIPTION
from cloudwatch_exporter.cloudwatch_exporter import create_service


def main(argv=None):
    common_kafka_cfg = get_kafka_service_config(SERVICE_NAME, argv)
    configure_logging(level=common_kafka_cfg.logging_level)

    logger = logging.getLogger(SERVICE_NAME)
    logger.info(f"Starting {SERVICE_NAME} Service: {SERVICE_DESCRIPTION}")
    logger.info(f"common_args = {common_kafka_cfg}")

    cloudwatch_exporter = create_service(common_kafka_cfg)
    cloudwatch_exporter.run_loop()


if __name__ == "__main__":
    main()
