import argparse
import logging
import abc
import time
import uuid

from configargparse import ArgParser
from signal import signal, SIGTERM
from bai_kafka_utils.kafka_client import create_kafka_consumer, create_kafka_producer
from bai_kafka_utils.events import BenchmarkEvent, VisitedService

from typing import List

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


class KafkaService:
    def __init__(self, args, callbacks: List[KafkaServiceCallback]):
        self.args = args

        self._producer_topic = args.producer_topic
        self._producer = create_kafka_producer(args.bootstrap_servers)
        self._consumer = create_kafka_consumer(args.bootstrap_servers,
                                               args.consumer_group_id,
                                               args.consumer_topic,
                                               args.event_payload_type)
        self.callbacks = callbacks
        signal(SIGTERM, self.stop_loop())

    def safe_handle_msg(self, msg, callback: KafkaServiceCallback) -> BenchmarkEvent:
        try:
            return self.handle_event(msg.value, callback)
        except:
            logger.exception(f"Failed to handle message: {msg}")

    def handle_event(self, event: BenchmarkEvent, callback: KafkaServiceCallback) -> BenchmarkEvent:
        """
        Utility method for handling a benchmark event.
        Does the logging and calls the callback funtion to handle the event
        :param event: event contained in the benchmark
        :param callback: implementation of KafkaServiceCallBack to handle the event
        """
        if not event:
            raise ValueError("Empty message received (no event found)")
        logger.debug(f"Got event {event}")
        return callback.handle_event(event)

    def send_event(self, event: BenchmarkEvent):
        """
        Base method for sending a event to Kafka.
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
        while True:
            # KafkaConsumer.poll() might return more than one message
            messages = self._consumer.poll()
            for msg in messages:
                for callback in self.callbacks:
                    output = self.safe_handle_msg(msg, callback)
                    self.send_event(output)

    def stop_loop(self):
        class SigtermReceived(Exception):
            pass

        for callback in self.callbacks:
            callback.cleanup()

        raise SigtermReceived
