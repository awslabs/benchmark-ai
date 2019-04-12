import os

from typing import List, Callable

from events.data_set import DataSet
from fetcher_dispatcher.data_set_manager import DataSetManager
from fetcher_dispatcher.data_set_pull import get_dataset_dst
from fetcher_dispatcher.kafka_client import kafka_consumer
from fetcher_dispatcher.kafka_client import kafka_producer


def main():
    data_set_mgr = DataSetManager()
    data_set_mgr.start()

    producer = kafka_producer()

    def extract_data_sets(msg) -> [DataSet]:
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

    BENCHMARK_TOPIC = os.environ.get("BENCHMARK_TOPIC", "benchmark_control")

    def handle_msg(msg):
        tasks = extract_data_sets(msg)
        tasks = list(filter(lambda t: not t.dst, tasks))

        if not tasks:
            return

        cb = lambda: producer.send(BENCHMARK_TOPIC, value=msg.value)
        execute_all(tasks, cb)

    for msg in kafka_consumer(BENCHMARK_TOPIC):
        handle_msg(msg)


if __name__ == '__main__':
    main()
