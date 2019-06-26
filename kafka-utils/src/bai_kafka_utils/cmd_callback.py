import dataclasses
import logging
from collections import OrderedDict
from inspect import signature

from typing import Any

from bai_kafka_utils.events import CommandRequestEvent, CommandResponsePayload, CommandRequestPayload
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService

logger = logging.getLogger(__name__)


class KafkaCommandCallback(KafkaServiceCallback):
    CODE_SUCCESS = 0
    CODE_COMMAND_ERROR = 1
    CODE_CLIENT_ERROR = 2

    OK = "Command was executed successfully"
    INVALID_ARGS = "Invalid args %s"

    def __init__(self, cmd_object: Any, cmd_return_topic: str):
        self.cmd_object = cmd_object
        self.cmd_return_topic = cmd_return_topic

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
            msg = KafkaCommandCallback.OK

            pos_args = []
            kw_args = {}

            if isinstance(args, list):
                pos_args = tuple(args)
            elif isinstance(args, dict):
                kw_args = args

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
                del params[k]

            from_event = vars(event)
            for key in from_event.keys() & params.keys():
                kw_args[key] = from_event[key]
            try:
                result = method(*pos_args, **kw_args)
            except TypeError as e:
                logger.exception("Method invocation failed")
                code = KafkaCommandCallback.CODE_CLIENT_ERROR
                msg = KafkaCommandCallback.INVALID_ARGS.format(str(e))
            except Exception as e:
                logger.exception("Command failed")
                code = KafkaCommandCallback.CODE_COMMAND_ERROR
                msg = str(e)

            response_payload = CommandResponsePayload(code, result, msg, event)
            response_event = dataclasses.replace(event, payload=response_payload)
            kafka_service.send_event(response_event, self.cmd_return_topic)
        else:
            logger.info(f"Uncallable {command} member requested")

    def cleanup(self):
        if hasattr(self.cmd_object, "cleanup"):
            self.cmd_object.cleanup()
