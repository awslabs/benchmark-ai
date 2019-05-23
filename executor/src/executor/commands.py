import subprocess
import logging

from bai_kafka_utils.events import CommandRequestEvent, CommandResponsePayload, CommandResponseEvent, create_from_object
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceCallbackException
from executor import SERVICE_NAME


logger = logging.getLogger(SERVICE_NAME)


class ExecutorCommandHandler(KafkaServiceCallback):
    LABEL_ACTION_ID = "action-id"
    LABEL_CREATED_BY = "created-by"

    # HACK: We need a way to find out the strategy used by a given action_id, so we can specify the types of resources
    # to delete accordingly. At the moment, this deletes all kinds of resources, which shouldn't be a problem since
    # we use the label selector to choose what gets deleted.
    ALL_K8S_RESOURCE_TYPES = "jobs,mpijobs,configmaps"

    def __init__(self, kubectl: str, producer_topic: str):
        self.kubectl = kubectl
        self.producer_topic = producer_topic

    def handle_event(self, event: CommandRequestEvent, kafka_service: KafkaService):
        command = event.payload.command
        args = event.payload.args

        if command.upper() == "DELETE":
            try:
                result = self._delete_job(args)
                return_code = 0
                msg = "Benchmark job successfully deleted"
            except subprocess.CalledProcessError as e:
                result = str(e)
                return_code = 1
                msg = "Error deleting benchmark job"
                logging.exception(f"Error processing DELETE command: {event}")
                raise KafkaServiceCallbackException from e
            finally:
                self._send_response_event(
                    kafka_service=kafka_service,
                    input_event=event,
                    return_code=return_code,
                    return_value=result,
                    msg=msg,
                )
        else:
            logging.warning(f"ERROR: Unknown command: {command}. Full event is {event}")
            self._send_response_event(
                kafka_service=kafka_service,
                input_event=event,
                return_code=1,
                return_value=f"Could not process command (unknown command {command})",
                msg="ERROR: Unknown command",
            )

    def _delete_job(self, args) -> str:
        action_id = args[0]
        label_selector = self._create_label_selector(action_id)
        resource_types = self.ALL_K8S_RESOURCE_TYPES

        cmd = [self.config.kubectl, "delete", resource_types, "--selector", label_selector]
        logger.info(f"Deleting resources of types {resource_types} matching selector {label_selector}")

        result = subprocess.check_output(cmd)
        logging.info(f"Succesfully deleted benchmark with id {action_id}")
        logger.info(f"Kubectl output: {result}")
        return result

    def _create_label_selector(self, action_id: str):
        return f"{self.LABEL_ACTION_ID}={action_id},{self.LABEL_CREATED_BY}={SERVICE_NAME}"

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
