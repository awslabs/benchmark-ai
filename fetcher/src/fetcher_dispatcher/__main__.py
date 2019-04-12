import os

from typing import List, Callable

from bai_common.events import DataSet
from fetcher_dispatcher.data_set_manager import DataSetManager
from fetcher_dispatcher.data_set_pull import get_dataset_dst
from fetcher_dispatcher.kafka_client import create_kafka_consumer
from fetcher_dispatcher.kafka_client import create_kafka_producer


def main():
    data_set_mgr = DataSetManager()
    data_set_mgr.start()

    producer = create_kafka_producer()

    def extract_data_sets(msg) -> List[DataSet]:
        return msg.value.payload.data_sets

    def execute(task: DataSet, callback) -> None:
        task.dst = get_dataset_dst(task.src)

        data_set_mgr.fetch(task, callback)

    def execute_all(tasks: List[DataSet], callback: Callable) -> None:

        pending = list(tasks)

        def on_done(data_set: DataSet):
            pending.remove(data_set)
            if not pending:
                callback()

        for tsk in tasks:
            execute(tsk, on_done)

    consumer_topic = os.environ.get("CONSUMER_TOPIC", "benchmark_control")
    producer_topic = os.environ.get("PRODUCER_TOPIC", consumer_topic)

    def handle_msg(msg):
        tasks = extract_data_sets(msg)
        tasks = list(filter(lambda t: not t.dst, tasks))

        if not tasks:
            return

        def on_all_done():
            producer.send(producer_topic, value=msg.value)

        execute_all(tasks, on_all_done)

    consumer = create_kafka_consumer(consumer_topic)
    for msg in consumer:
        handle_msg(msg)


if __name__ == '__main__':
    main()
