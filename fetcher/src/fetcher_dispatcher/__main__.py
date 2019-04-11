import os

from fetcher_dispatcher.data_set_manager import DataSetManager
from fetcher_dispatcher.data_set_pull import get_dataset_dst
from fetcher_dispatcher.events.data_set import DataSet
from fetcher_dispatcher.kafka_client import kafka_consumer
from fetcher_dispatcher.kafka_client import kafka_producer

DEFAULT_ENCODING = os.environ.get("DEFAULT_ENCODING", "utf-8")

data_set_mgr = DataSetManager()
data_set_mgr.start()

producer = kafka_producer()


def dict_to_data_set(task: DataSet):
    return DataSet(task["src"], task.get("dst", ""), task.get("md5", ""))


def extract_data_sets(msg) -> [DataSet]:
    return msg.value.payload.data_sets


def execute(task: DataSet, callback) -> None:
    task.dst = get_dataset_dst(task.src)

    data_set_mgr.fetch(task, callback)


def execute_all(tasks: [DataSet], callback) -> None:
    cb = lambda: callback()
    for tsk in tasks:
        execute(tsk, cb)


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
