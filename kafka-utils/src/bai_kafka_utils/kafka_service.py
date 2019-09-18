import abc
import dataclasses
import itertools
import logging
from dataclasses import dataclass
from signal import signal, SIGTERM
from typing import List, Optional, Dict

from kafka import KafkaProducer, KafkaConsumer

from bai_kafka_utils.events import BenchmarkEvent, Status
from bai_kafka_utils.events import VisitedService, StatusMessageBenchmarkEvent
from bai_kafka_utils.utils import generate_uuid, now_milliseconds

logger = logging.getLogger(__name__)

KAFKA_POLL_INTERVAL_MS = 500

# Default values
DEFAULT_NUM_PARTITIONS = 3
DEFAULT_REPLICATION_FACTOR = 3


@dataclass()
class KafkaServiceConfig:
    consumer_topic: str
    producer_topic: str
    bootstrap_servers: List[str]
    logging_level: str
    cmd_submit_topic: Optional[str] = None
    cmd_return_topic: Optional[str] = None
    status_topic: Optional[str] = None
    consumer_group_id: Optional[str] = None
    num_partitions: Optional[int] = DEFAULT_NUM_PARTITIONS
    replication_factor: Optional[int] = DEFAULT_REPLICATION_FACTOR


class KafkaServiceCallback(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def handle_event(self, event: BenchmarkEvent, kafka_service):
        pass

    @abc.abstractmethod
    def cleanup(self):
        pass


class EventEmitter:
    """
    Encapsulates logic required to emit status and regular (benchmark, command, etc.) events
    """

    def __init__(
        self, name: str, version: str, pod_name: str, status_topic: Optional[str], kakfa_producer: KafkaProducer
    ):
        self.name = name
        self.version = version
        self.pod_name = pod_name
        self._status_topic = status_topic
        self._kafka_producer = kakfa_producer

    def send_status_message_event(
        self, handled_event: BenchmarkEvent, status: Status, msg: str, target_action_id: Optional[str] = None
    ):
        """
        Utility method for sending status message events.
        :param status: status of the event
        :param handled_event: value of the message to send
        :param msg: Message to send
        :param target_action_id: The action id against which the status message should be registered. If
        not set, the action id of the source event will be used.
        """
        status_event = StatusMessageBenchmarkEvent.create_from_event(status, msg, handled_event)

        if target_action_id:
            status_event.action_id = target_action_id

        if not self._status_topic:
            logger.info(f"No status topic specified. Losing event: {status_event}")
            return

        self.send_event(status_event, self._status_topic)

    def send_event(self, event: BenchmarkEvent, topic: str):
        """
        Base method for sending an event to Kafka.
        Adds this service to the visited field in the event and calls the KafkaProducer.
        :param event: value of the message to send
        :param topic: topic to send to
        """

        def add_self_to_visited(src_event):
            current_time_ms = now_milliseconds()
            entry = VisitedService(self.name, current_time_ms, self.version, self.pod_name)
            res = list(src_event.visited)
            res.append(entry)
            return res

        event_to_send = dataclasses.replace(
            event, message_id=generate_uuid(), type=topic, visited=add_self_to_visited(event), tstamp=now_milliseconds()
        )
        event_key = event_to_send.client_id

        logger.info(f"Sending {event_to_send} -> {topic}")
        self._kafka_producer.send(topic, value=event_to_send, key=event_key)


class KafkaServiceCallbackException(Exception):
    pass


class KafkaService:
    class LoopAlreadyRunningException(Exception):
        pass

    class LoopNotRunningException(Exception):
        pass

    def __init__(
        self,
        name: str,
        version: str,
        callbacks: Dict[str, List[KafkaServiceCallback]],
        kafka_consumer: KafkaConsumer,
        kafka_producer: KafkaProducer,
        pod_name: str,
        status_topic: Optional[str] = None,
    ):

        self._event_emitter = EventEmitter(
            name=name, version=version, pod_name=pod_name, status_topic=status_topic, kakfa_producer=kafka_producer
        )

        self._name = name
        self._pod_name = pod_name
        self._consumer = kafka_consumer

        # Immutability helps us to avoid nasty bugs.
        self._callbacks = {topic: list(callbacks) for topic, callbacks in callbacks.items()}

        self._running = False
        signal(SIGTERM, self.stop_loop)

    _LOOP_IS_ALREADY_RUNNING = "Loop is already running"
    _IS_NOT_RUNNING = "Loop is not running"
    _CANNOT_UPDATE_CALLBACKS = "Cannot update callbacks with running loop"

    def name(self, name):
        self._name = name

    def pod_name(self, pod_name):
        self._pod_name = pod_name

    def safe_handle_msg(self, msg, callback: KafkaServiceCallback):
        # noinspection PyBroadException
        try:
            self.handle_event(msg.value, callback)
        except KafkaServiceCallbackException:
            logger.exception(f"Failed to handle message: {msg}")
        except Exception:
            # TODO: Stop catching this and push failed submissions to a dead letter queue
            logger.exception(f"Unknown error handling message: {msg}")

    def handle_event(self, event: BenchmarkEvent, callback: KafkaServiceCallback):
        """
        Utility method for handling a benchmark event.
        Does the logging and calls the callback function to handle the event
        :param event: event contained in the benchmark
        :param callback: implementation of KafkaServiceCallBack to handle the event
        """
        if not event:
            raise KafkaServiceCallbackException("Empty message received (no event found)")
        logger.info(f"Got event {event}")
        logging.debug(f"{self.name} service, node {self.pod_name}: Processing event...")
        callback.handle_event(event, self)

    def send_status_message_event(
        self, handled_event: BenchmarkEvent, status: Status, msg: str, target_action_id: Optional[str] = None
    ):
        self._event_emitter.send_status_message_event(handled_event, status, msg, target_action_id)

    def send_event(self, event: BenchmarkEvent, topic: str):
        self._event_emitter.send_event(event, topic)

    @property
    def running(self) -> bool:
        return self._running

    def run_loop(self):
        if self._running:
            raise KafkaService.LoopAlreadyRunningException(KafkaService._LOOP_IS_ALREADY_RUNNING)

        self._running = True

        while self._running:
            # KafkaConsumer.poll() might return more than one message
            records = self._consumer.poll(KAFKA_POLL_INTERVAL_MS)

            for topic_partition, record in records.items():
                topic = topic_partition.topic
                for msg in record:
                    if msg.value and not msg.value.type == topic:
                        logger.warning(f"Unexpected event type {msg.value.type} in topic {topic}")
                    if topic not in self._callbacks:
                        logger.warning(
                            f"Message received but not processed: {msg} \n" f"(No callbacks assigned to topic {topic})"
                        )
                    else:
                        logger.info("Processing message over {} callbacks".format(len(self._callbacks[topic])))
                        for callback in self._callbacks[topic]:
                            self.safe_handle_msg(msg, callback)

        distinct_callbacks = set(itertools.chain.from_iterable(self._callbacks.values()))
        for callback in distinct_callbacks:
            callback.cleanup()

    def stop_loop(self):
        if not self._running:
            raise KafkaService.LoopNotRunningException(KafkaService._IS_NOT_RUNNING)

        self._running = False

    def add_callback(self, callback: KafkaServiceCallback, topic: str):
        if self._running:
            raise KafkaService.LoopAlreadyRunningException(KafkaService._CANNOT_UPDATE_CALLBACKS)

        if topic in self._callbacks:
            self._callbacks[topic].append(callback)
        else:
            self._callbacks[topic] = [callback]

    def remove_callback(self, callback: KafkaServiceCallback, topic: str = None):
        if self._running:
            raise KafkaService.LoopAlreadyRunningException(KafkaService._CANNOT_UPDATE_CALLBACKS)

        if topic:
            self._callbacks[topic].remove(callback)
        else:
            for cbs in self._callbacks.values():
                if callback in cbs:
                    cbs.remove(callback)
