import logging
import os


from bai_kafka_utils.kafka_service_args import get_kafka_service_config
from bai_kafka_utils.logging import configure_logging

from sm_executor import SERVICE_NAME, SERVICE_DESCRIPTION
from sm_executor.args import create_executor_config


def main(argv=None):
    import pydevd

    pydevd.settrace("localhost", port=21000, suspend=False)

    common_kafka_cfg = get_kafka_service_config(SERVICE_NAME, argv)
    executor_config = create_executor_config(argv, os.environ)

    configure_logging(level=common_kafka_cfg.logging_level)

    logger = logging.getLogger(SERVICE_NAME)
    logger.info(f"Starting {SERVICE_NAME} Service: {SERVICE_DESCRIPTION}")
    logger.info(f"common_args = {common_kafka_cfg}")
    logger.info(f"executor_args = {executor_config}")

    from sm_executor.sm_executor import create_executor

    executor = create_executor(common_kafka_cfg, executor_config)
    executor.run_loop()


if __name__ == "__main__":
    main()
