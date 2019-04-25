import abc
import argparse
import logging
import time
import uuid
from signal import signal, SIGTERM
from typing import List, Type

from configargparse import ArgParser

from bai_kafka_utils.events import BenchmarkEvent, VisitedService, BenchmarkPayload
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer

logger = logging.getLogger(__name__)


def create_kafka_service_parser(program_name: str) -> ArgParser:
    def create_split_action(delimiter: str):
        class customAction(argparse.Action):
            def __call__(self, parser, args, values, option_string=None):
                setattr(args, self.dest, values.split(delimiter))

        return customAction

    parser = ArgParser(auto_env_var_prefix="",
                                           prog=program_name)

    parser.add_argument("--consumer-topic",
                        env_var='CONSUMER_TOPIC',
                        required=True)

    parser.add_argument("--producer-topic",
                        env_var='PRODUCER_TOPIC',
                        required=True)

    parser.add_argument("--bootstrap-servers",
                        env_var="KAFKA_BOOTSTRAP_SERVERS",
                        default="localhost:9092",
                        action=create_split_action(','))

    parser.add_argument("--consumer-group-id",
                        env_var="CONSUMER_GROUP_ID")

    parser.add_argument("--logging-level",
                        env_var="LOGGING_LEVEL",
                        default="INFO")

    return parser


class KafkaServiceCallback(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def handle_event(self, event: BenchmarkEvent):
        pass

    @abc.abstractmethod
    def cleanup(self):
        pass


class KafkaServiceCallbackException(Exception):
    pass


class KafkaService:
    def __init__(self,
                 name: str,
                 version: str,
                 payload_type: Type[BenchmarkPayload],
                 args,
                 callbacks: List[KafkaServiceCallback]):

        self.args = args

        self._producer_topic = args.producer_topic
        self._producer = create_kafka_producer(args.bootstrap_servers)
        self._consumer = create_kafka_consumer(args.bootstrap_servers,
                                               args.consumer_group_id,
                                               args.consumer_topic,
                                               args.event_payload_type)
        self.name = name
        self.version = version
        self.payload_type = payload_type

        self.callbacks = callbacks
        self.running = False
        signal(SIGTERM, self.stop_loop())

    def safe_handle_msg(self, msg, callback: KafkaServiceCallback) -> BenchmarkEvent:
        try:
            return self.handle_event(msg.value, callback)
        except KafkaServiceCallbackException:
            logger.exception(f"Failed to handle message: {msg}")

    def handle_event(self, event: BenchmarkEvent, callback: KafkaServiceCallback) -> BenchmarkEvent:
        """
        Utility method for handling a benchmark event.
        Does the logging and calls the callback funtion to handle the event
        :param event: event contained in the benchmark
        :param callback: implementation of KafkaServiceCallBack to handle the event
        """
        if not event:
            raise KafkaServiceCallbackException("Empty message received (no event found)")
        logger.debug(f"Got event {event}")
        return callback.handle_event(event)

    def send_event(self, event: BenchmarkEvent):
        """
        Base method for sending an event to Kafka.
        Adds this service to the visited field in the event and calls the KafkaProducer.
        :param event: value of the message to send
        """
        def add_self_to_visited(event):
            entry = VisitedService(self.args.name,
                                   int(time.time() * 1000),
                                   self.args.version)
            event.visited.append(entry)

        # Message ID is unique per message
        event.message_id = str(uuid.uuid4())
        add_self_to_visited(event)

        self._producer.send(self._producer_topic,
                            value=event)

    def run_loop(self):
        if self.running:
            raise ValueError("Loop is already running")

        self.running = True

        while self.running:
            # KafkaConsumer.poll() might return more than one message
            # TODO: Do we need a timeout here? (timeout_ms parameter)
            messages = self._consumer.poll()
            for msg in messages:
                for callback in self.callbacks:
                    output = self.safe_handle_msg(msg, callback)
                    self.send_event(output)

        for callback in self.callbacks:
            callback.cleanup()

    def stop_loop(self):
        if not self.running:
            raise ValueError("Loop is not running")

        self.running = False
