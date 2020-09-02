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
import os

from executor import SERVICE_NAME, SERVICE_DESCRIPTION
from executor.executor import create_executor
from executor.args import create_executor_config
from bai_kafka_utils.kafka_service_args import get_kafka_service_config
from bai_kafka_utils.logging import configure_logging


def main(argv=None):
    common_kafka_cfg = get_kafka_service_config(SERVICE_NAME, argv)
    executor_config = create_executor_config(argv, os.environ)

    configure_logging(level=common_kafka_cfg.logging_level)

    logger = logging.getLogger(SERVICE_NAME)
    logger.info(f"Starting {SERVICE_NAME} Service: {SERVICE_DESCRIPTION}")
    logger.info(f"common_args = {common_kafka_cfg}")
    logger.info(f"executor_args = {executor_config}")

    executor = create_executor(common_kafka_cfg, executor_config)
    executor.run_loop()


if __name__ == "__main__":
    main()
