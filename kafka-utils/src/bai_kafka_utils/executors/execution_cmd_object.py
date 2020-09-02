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

from typing import Dict

from bai_kafka_utils.events import CommandRequestEvent
from bai_kafka_utils.executors.execution_callback import (
    ExecutionEngine,
    Status,
    ExecutionEngineException,
    NoResourcesFoundException,
)
from bai_kafka_utils.kafka_service import KafkaService

logger = logging.getLogger(__name__)


class ExecutorCommandObject:
    def __init__(self, execution_engines: Dict[str, ExecutionEngine]):
        self.execution_engines = execution_engines

    def cancel(
        self,
        kafka_service: KafkaService,
        event: CommandRequestEvent,
        client_id: str,
        target_action_id: str,
        cascade: bool = False,
    ):
        for engine in set(self.execution_engines.values()):
            try:
                result = engine.cancel(client_id, target_action_id, cascade)
            except ExecutionEngineException as err:
                if isinstance(err, NoResourcesFoundException):
                    logger.info(f"No resources found for {target_action_id}")
                else:
                    kafka_service.send_status_message_event(
                        event,
                        Status.FAILED,
                        f"An error occurred when attempting to delete resources related to {target_action_id}. "
                        f"Please check the status of the deletion command ({event.action_id} "
                        f"for additional information.",
                        target_action_id,
                    )
                raise err

            # issue event under the target action_id
            kafka_service.send_status_message_event(
                event, Status.SUCCEEDED, "Execution successfully cancelled...", target_action_id
            )

            return result
