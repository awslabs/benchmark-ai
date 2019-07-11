from typing import Callable, List

from kafka import KafkaConsumer
from timeout_decorator import timeout

from bai_kafka_utils.events import BenchmarkEvent
from bai_kafka_utils.integration_tests.test_utils import get_test_timeout

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
