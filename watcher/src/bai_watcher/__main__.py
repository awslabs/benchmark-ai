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
def main(argv=None):
    from bai_kafka_utils.kafka_service_args import get_kafka_service_config
    from bai_kafka_utils.logging import configure_logging
    from bai_watcher import SERVICE_NAME, SERVICE_DESCRIPTION
    from bai_watcher.args import get_watcher_service_config

    common_kafka_cfg = get_kafka_service_config(SERVICE_NAME, argv)
    service_cfg = get_watcher_service_config(argv)

    configure_logging(level=common_kafka_cfg.logging_level)

    from bai_watcher import service_logger

    service_logger.setLevel(service_cfg.logging_level)

    from bai_watcher.kafka_service_watcher import create_service

    logger = service_logger.getChild(SERVICE_NAME)
    logger.info(f"Starting {SERVICE_NAME} Service: {SERVICE_DESCRIPTION}")
    logger.info("common_args = %s", common_kafka_cfg)
    logger.info("service_specific_args = %s", service_cfg)

    service = create_service(common_kafka_cfg, service_cfg)
    service.run_loop()


if __name__ == "__main__":
    main()
