from typing import Callable, List

from kafka import KafkaConsumer
from timeout_decorator import timeout

from bai_kafka_utils.events import BenchmarkEvent, Status, CommandRequestEvent, CommandResponsePayload
from bai_kafka_utils.integration_tests.test_utils import get_test_timeout
from bai_kafka_utils.kafka_service import KafkaServiceConfig

WAIT_TIMEOUT = get_test_timeout()
POLL_TIMEOUT_MS = 500

EventFilter = Callable[[BenchmarkEvent], bool]


class CombinedFilter(EventFilter):
    def __init__(self, filters: List[EventFilter]):
        self.set_filters = set(filters)

    # Returns true after all filters are satisfied
    def __call__(self, event: BenchmarkEvent) -> bool:
        for event_filter in self.set_filters:
            if event_filter(event):
                self.set_filters.remove(event_filter)
                print(f"Hit condition {event_filter.__name__}. {len(self.set_filters)} to hit.")
                break
        return not self.set_filters


@timeout(WAIT_TIMEOUT)
def wait_for_response(filter_event: EventFilter, kafka_consumer_of_produced: KafkaConsumer):
    while True:
        records = kafka_consumer_of_produced.poll(POLL_TIMEOUT_MS)
        print("Got this:")
        print(records)
        kafka_consumer_of_produced.commit()
        for topic, recs in records.items():
            for msg in recs:
                print(f"Got event {msg.value}")
                if filter_event(msg.value):
                    return


def get_is_status_filter(
    src_event: BenchmarkEvent, status: Status, kafka_service_config: KafkaServiceConfig
) -> EventFilter:
    def filter_status_event(event: BenchmarkEvent) -> bool:
        return (
            event.type == kafka_service_config.status_topic
            and event.action_id == src_event.action_id
            and event.status == status
        )

    return filter_status_event


def get_is_command_return_filter(
    src_event: CommandRequestEvent, return_code: int, kafka_service_config: KafkaServiceConfig
) -> EventFilter:
    def filter_command_event(event: BenchmarkEvent) -> bool:
        if event.type != kafka_service_config.cmd_return_topic or not isinstance(event.payload, CommandResponsePayload):
            return False
        payload: CommandResponsePayload = event.payload
        return (
            payload.return_code == return_code
            and payload.cmd_submit.action_id == src_event.action_id
            and payload.cmd_submit.payload == src_event.payload
        )

    return filter_command_event
