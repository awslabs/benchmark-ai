import logging

from executor import SERVICE_NAME, SERVICE_DESCRIPTION
from executor.executor import create_executor
from executor.args import create_executor_config
from bai_kafka_utils.kafka_service_args import get_kafka_service_config
from bai_kafka_utils.utils import set_logging_level_and_format


def main(argv=None):
    common_kafka_cfg = get_kafka_service_config(SERVICE_NAME, argv)
    executor_config = create_executor_config(argv)

    set_logging_level_and_format(level=common_kafka_cfg.logging_level)

    logger = logging.getLogger(SERVICE_NAME)
    logger.info(f"Starting {SERVICE_NAME} Service: {SERVICE_DESCRIPTION}")
    logger.info(f"common_args = {common_kafka_cfg}")
    logger.info(f"executor_args = {executor_config}")

    executor = create_executor(common_kafka_cfg, executor_config)
    executor.run_loop()


if __name__ == "__main__":
    main()
