import logging

from bai_kafka_utils.kafka_service_args import get_kafka_service_config
from bai_watcher import SERVICE_NAME, SERVICE_DESCRIPTION
from bai_watcher.args import get_watcher_service_config
from bai_watcher.watcher import create_service


def main(argv=None):
    common_kafka_cfg = get_kafka_service_config(SERVICE_NAME, argv)
    service_cfg = get_watcher_service_config(argv)

    logging.basicConfig(level=common_kafka_cfg.logging_level)

    logger = logging.getLogger(SERVICE_NAME)
    logger.info(f"Starting {SERVICE_NAME} Service: {SERVICE_DESCRIPTION}")
    logger.info("common_args = %s", common_kafka_cfg)
    logger.info("service_specific_args = %s", service_cfg)

    service = create_service(common_kafka_cfg, service_cfg)
    service.run_loop()


if __name__ == "__main__":
    main()
