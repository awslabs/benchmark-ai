import logging
from collections import OrderedDict
from inspect import signature

from typing import Any

from bai_kafka_utils.events import (
    CommandRequestEvent,
    CommandResponsePayload,
    CommandRequestPayload,
    create_from_object,
    CommandResponseEvent,
)
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService

logger = logging.getLogger(__name__)


class KafkaCommandCallback(KafkaServiceCallback):
    CODE_SUCCESS = 0
    CODE_COMMAND_ERROR = 1
    CODE_CLIENT_ERROR = 2

    OK = "{} command processed successfully"
    INVALID_ARGS = "{} command failed: Invalid args {}"
    UNKNOWN_ERROR = "{} command failed: Unknown error with message '{}'"

    def __init__(self, cmd_object: Any, cmd_return_topic: str):
        self.cmd_object = cmd_object
        self.cmd_return_topic = cmd_return_topic

    @staticmethod
    def _get_message(fmt: str, command, *args, **kwargs):
        return fmt.format(command.capitalize(), *args, **kwargs)

    def handle_event(self, event: CommandRequestEvent, kafka_service: KafkaService):
        # Safety check
        payload = event.payload
        if not payload or not isinstance(payload, CommandRequestPayload):
            logger.info("Wrong payload passed")
            return

        command = event.payload.command
        args = event.payload.args

        logger.info(f"Command {command} called with {args}")

        if not hasattr(self.cmd_object, command):
            # May be another callback in the chain will be able to handle it
            logger.info("No command method found")
            return
        method = getattr(self.cmd_object, command)

        if callable(method):
            sig = signature(method)

            result = None
            code = KafkaCommandCallback.CODE_SUCCESS
            msg = self._get_message(KafkaCommandCallback.OK, command)

            pos_args = []
            kw_args = {}

            if isinstance(args, list):
                pos_args = tuple(args)
            elif isinstance(args, dict):
                kw_args = dict(args)

            if "event" in sig.parameters:
                kw_args["event"] = event
            if "kafka_service" in sig.parameters:
                kw_args["kafka_service"] = kafka_service

            params = OrderedDict(sig.parameters)

            # Remove positionals
            orderparams = list(params)
            for i in range(0, min(len(pos_args), len(orderparams))):
                del params[orderparams[i]]

            # Remove named
            for k in kw_args:
                if k in params:
                    del params[k]

            from_event = vars(event)
            for key in from_event.keys() & params.keys():
                kw_args[key] = from_event[key]
            try:
                logger.info(f"executing {command}({pos_args}, {kw_args})")
                result = method(*pos_args, **kw_args)
            except TypeError as e:
                logger.exception("Method invocation failed")
                code = KafkaCommandCallback.CODE_CLIENT_ERROR
                msg = self._get_message(KafkaCommandCallback.INVALID_ARGS, command, str(e))
            except Exception as e:
                logger.exception("Command failed")
                code = KafkaCommandCallback.CODE_COMMAND_ERROR
                msg = self._get_message(KafkaCommandCallback.UNKNOWN_ERROR, command, str(e))

            response_payload = CommandResponsePayload(code, msg, event, result)
            response_event = create_from_object(CommandResponseEvent, event, payload=response_payload)
            kafka_service.send_event(response_event, self.cmd_return_topic)
        else:
            logger.info(f"Uncallable {command} member requested")

    def cleanup(self):
        if hasattr(self.cmd_object, "cleanup"):
            self.cmd_object.cleanup()
