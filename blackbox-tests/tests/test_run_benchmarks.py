import dataclasses
import sys
from builtins import TimeoutError
from bai_kafka_utils.events import Status, StatusMessageBenchmarkEvent
from typing import Iterable, Iterator
from collections import namedtuple
from pathlib import Path
from bai_client.client import BaiClient
from pprint import pprint
import datetime
import time
import pytest
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level="DEBUG")


@pytest.fixture(scope="module")
def client(bff_endpoint):
    yield BaiClient(endpoint=bff_endpoint)


def generator_status_messages(
    bai_client,
    action_id,
    *,
    sleep_between_status_checks=datetime.timedelta(milliseconds=500),
    timeout=datetime.timedelta(minutes=10),
    callback_on_every_status_check=lambda: None,
) -> Iterator[StatusMessageBenchmarkEvent]:
    """
    Generates `StatusInfo` objects by querying the Status API of BFF.

    This is an infinite stream which will generate events until a timeout happens, which raises a TimeoutError if it
    reaches that point.

    :param bai_client:
    :param action_id:
    :param sleep_between_status_checks:
    :param timeout:
    :param callback_on_every_status_check:
    :return:
    """
    deadline = datetime.datetime.utcnow() + timeout
    index_of_last_status = 0
    while deadline > datetime.datetime.utcnow():
        time.sleep(sleep_between_status_checks.total_seconds())
        status_messages = bai_client.status(action_id)
        callback_on_every_status_check()

        if status_messages is None:
            logger.info("Status is None")
            continue

        if len(status_messages) == 0:
            logger.info("No status messages obtained")
            continue

        status_infos_to_print = status_messages[index_of_last_status:]
        for status_info in status_infos_to_print:
            yield status_info
        index_of_last_status = len(status_messages)
    else:
        raise TimeoutError()


def check_for_benchmark_completion(bai_client, action_id):
    def print_progress():
        sys.stdout.write(".")

    status_messages = generator_status_messages(bai_client, action_id, callback_on_every_status_check=print_progress)
    for status_message in status_messages:
        print()
        service = status_message.visited[-1].svc
        print(f"Benchmark Status: [{service}] - {status_message.payload.status}: {status_message.payload.message}")
        if status_message.payload.status in [Status.FAILED, Status.ERROR]:
            print(f"Benchmark finished with error in {service}: {status_message.payload.status}")
            return False
        if service == "watcher" and status_message.payload.status == Status.SUCCEEDED:
            print("Benchmark finished with success")
            return True
        sys.stdout.flush()


def unique_justseen(objects: Iterable) -> Iterable:
    last = None
    for obj in objects:
        if last is not None and obj == last:
            continue
        yield obj
        last = obj


def get_sample_benchmark_descriptor_filepath(benchmark) -> Path:
    from os.path import abspath
    from os.path import dirname
    from os.path import join

    here = abspath(dirname(__file__))
    bai_project_path = Path(abspath(join(here, "..", "..")))
    sample_benchmark_path = bai_project_path / "sample-benchmarks" / benchmark
    if not sample_benchmark_path.exists():
        raise ValueError(f"Sample benchmark {benchmark} does not exist. Looked at path {sample_benchmark_path}")
    return sample_benchmark_path


@pytest.mark.parametrize(
    "descriptor_filename",
    [
        "hello-world/descriptor.toml",
        # ("single-node", "descriptor_cpu.toml"),
        # ("single-node", "descriptor_gpu.toml"),
    ],
)
def test_sample_benchmarks(client, descriptor_filename):
    print(f"Starting test for {descriptor_filename}")
    full_path = str(get_sample_benchmark_descriptor_filepath(descriptor_filename))
    status_code = client.ping()
    assert status_code == 200
    action_id = client.submit(full_path)
    print(f"action-id={action_id}")
    passed = check_for_benchmark_completion(client, action_id)
    assert passed
    status_messages = client.status(action_id)
    print("#" * 120)
    print("# Status messages (for debugging)")
    print("#" * 120)
    for status_message in status_messages:
        pprint(dataclasses.asdict(status_message))
        print("-" * 80)

    # Events statuses
    ServiceAndStatus = namedtuple("T", ("visited_service", "status"))
    events = (
        ServiceAndStatus(visited_service=message.visited[-1].svc, status=message.payload.status)
        for message in status_messages
    )
    events = unique_justseen(events)
    events = set(events)
    assert events == {
        ServiceAndStatus("bai-bff", Status.SUCCEEDED),
        ServiceAndStatus("fetcher-dispatcher", Status.SUCCEEDED),
        ServiceAndStatus("executor", Status.PENDING),
        ServiceAndStatus("executor", Status.SUCCEEDED),
        ServiceAndStatus("watcher", Status.PENDING),
        ServiceAndStatus("watcher", Status.RUNNING),
        ServiceAndStatus("watcher", Status.SUCCEEDED),
        ServiceAndStatus("watcher", Status.METRICS_AVAILABLE),
    }

    # All visited services
    visited_services = [visited.svc for msg in status_messages for visited in msg.visited]
    visited_services = set(visited_services)
    assert visited_services == {"anubis-client", "bai-bff", "fetcher-dispatcher", "executor", "watcher"}
