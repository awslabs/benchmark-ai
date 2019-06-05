import subprocess
import logging
from typing import List

from bai_kafka_utils.events import CommandRequestEvent, CommandResponsePayload, CommandResponseEvent, create_from_object
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceCallbackException
from executor import SERVICE_NAME


logger = logging.getLogger(SERVICE_NAME)


class ExecutorCommandHandler(KafkaServiceCallback):
    LABEL_ACTION_ID = "action-id"
    LABEL_CREATED_BY = "created-by"
    LABEL_CLIENT_ID = "client-id"

    # HACK: We need a way to find out the strategy used by a given action_id, so we can specify the types of resources
    # to delete accordingly. At the moment, this deletes all kinds of resources, which shouldn't be a problem since
    # we use the label selector to choose what gets deleted.
    ALL_K8S_RESOURCE_TYPES = ["jobs", "mpijobs", "configmaps"]

    def __init__(self, kubectl: str, producer_topic: str):
        self.kubectl = kubectl
        self.producer_topic = producer_topic

    def handle_event(self, event: CommandRequestEvent, kafka_service: KafkaService):
        command = event.payload.command
        args = event.payload.args
        client_id = event.client_id

        if command.upper() == "DELETE":
            try:
                result = self._delete_benchmark(args, client_id)
                self._send_response_event(
                    kafka_service=kafka_service,
                    input_event=event,
                    return_code=0,
                    return_value=result,
                    msg="Benchmark job successfully deleted",
                )
            except (subprocess.CalledProcessError, IndexError, ValueError) as e:
                self._send_response_event(
                    kafka_service=kafka_service,
                    input_event=event,
                    return_code=1,
                    return_value=str(e),
                    msg="Error deleting benchmark job",
                )
                logging.exception(f"Error processing DELETE command: {event}")
                raise KafkaServiceCallbackException from e
        else:
            logging.warning(f"ERROR: Unknown command: {command}. Full event is {event}")
            self._send_response_event(
                kafka_service=kafka_service,
                input_event=event,
                return_code=1,
                return_value=f"Could not process command (unknown command {command})",
                msg="ERROR: Unknown command",
            )
            raise KafkaServiceCallbackException(f"Unknown command {command}")

    def _delete_benchmark(self, args: List[str], client_id: str) -> str:
        try:
            action_id = args[0]
        except IndexError:
            logging.exception(f"Command is missing an argument: action_id")
            raise

        label_selector = self._create_label_selector(action_id, client_id)
        resource_types = ",".join(self.ALL_K8S_RESOURCE_TYPES)

        cmd = [self.kubectl, "delete", resource_types, "--selector", label_selector]
        logger.info(f"Deleting resources of types {resource_types} matching selector {label_selector}")

        result = subprocess.check_output(cmd)

        # kubectl delte exits with 0 even if there are no resources to delete, so we need to handle that case ourselves
        if "No resources found" in result:
            raise ValueError(f"No resources found matching selector {label_selector}")

        logging.info(f"Succesfully deleted benchmark with id {action_id}")
        logger.info(f"Kubectl output: {result}")
        return result

    def _create_label_selector(self, action_id: str, client_id: str):
        return (
            f"{self.LABEL_ACTION_ID}={action_id},"
            f"{self.LABEL_CREATED_BY}={SERVICE_NAME},"
            f"{self.LABEL_CLIENT_ID}={client_id}"
        )

    def _send_response_event(
        self,
        kafka_service: KafkaService,
        input_event: CommandRequestEvent,
        return_code: int,
        return_value: str,
        msg: str,
    ):
        payload = CommandResponsePayload(
            return_code=return_code, return_value=return_value, message=msg, cmd_submit=input_event
        )
        response = create_from_object(CommandResponseEvent, input_event, payload=payload)
        kafka_service.send_event(response, topic=self.producer_topic)

    def cleanup(self):
        pass
