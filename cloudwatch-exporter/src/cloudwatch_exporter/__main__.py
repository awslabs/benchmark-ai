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
