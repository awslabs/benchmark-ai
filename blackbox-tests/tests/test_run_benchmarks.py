import os
import sys
from builtins import TimeoutError
from contextlib import contextmanager

import subprocess
import tempfile

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

logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)


@contextmanager
def create_client():
    # HACK: Port forwarding because BFF is not currently exposed to the world as a service
    #       https://github.com/MXNetEdge/benchmark-ai/issues/454
    dirname = os.path.dirname(sys.executable)
    with tempfile.NamedTemporaryFile("w+", prefix="bai-blackbox-", suffix=".kubeconfig") as kubeconfig_file:
        eks_update_kubeconfig_command = (
            f"{dirname}/aws eks update-kubeconfig --name benchmark-cluster --kubeconfig {kubeconfig_file.name}"
        )
        print(f"Executing: {eks_update_kubeconfig_command}")
        subprocess.check_output(eks_update_kubeconfig_command.split(" "))
        port_forward_command = (
            f"{dirname}/kubectl --kubeconfig={kubeconfig_file.name} port-forward deployment/bai-bff 8080"
        )
        print(f"Executing: {port_forward_command}")
        with subprocess.Popen(port_forward_command.split(" "), stdout=subprocess.PIPE) as port_forward_process:
            try:
                while True:
                    retcode = port_forward_process.poll()
                    if retcode:
                        print("Output of `kubectl port-forward`: '%s'" % port_forward_process.stdout.read())
                        raise ValueError(f"Port-forward command returned with exitcode: {retcode}")
                    line = port_forward_process.stdout.readline()
                    line = line.decode("utf-8")
                    print(line)
                    if "Forwarding from 127.0.0.1:8080 -> 8080" in line:
                        break
                yield BaiClient(endpoint="http://localhost:8080")
            finally:
                port_forward_process.kill()


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


def wait_for_benchmark_completion(bai_client, action_id):
    def print_progress():
        sys.stdout.write(".")

    status_messages = generator_status_messages(bai_client, action_id, callback_on_every_status_check=print_progress)
    for status_message in status_messages:
        print()
        service = status_message.visited[-1].svc
        print(f"Benchmark Status: [{service}] - {status_message.status}: {status_message.message}")
        if status_message.status in [Status.FAILED, Status.ERROR]:
            print(f"Benchmark finished with error in {service}: {status_message.status}")
            return
        if service == "watcher" and status_message.status == Status.SUCCEEDED:
            print("Benchmark finished with success")
            return
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
def test_sample_benchmarks(descriptor_filename):
    print(f"Starting test for {descriptor_filename}")
    full_path = str(get_sample_benchmark_descriptor_filepath(descriptor_filename))
    with create_client() as client:
        action_id = client.submit(full_path)
        print(f"action_id={action_id}")
        wait_for_benchmark_completion(client, action_id)
        status_messages = client.status(action_id)
    print("#" * 120)
    print("# Status messages (for debugging)")
    print("#" * 120)
    pprint(status_messages)

    ServiceAndStatus = namedtuple("T", ("visited_service", "status"))
    events = (
        ServiceAndStatus(visited_service=message.visited[-1].svc, status=message.status) for message in status_messages
    )
    events = unique_justseen(events)
    events = list(events)

    assert events == [
        ServiceAndStatus("fetcher-dispatcher", Status.PENDING),
        ServiceAndStatus("fetcher-dispatcher", Status.SUCCEEDED),
        ServiceAndStatus("executor", Status.PENDING),
        ServiceAndStatus("executor", Status.SUCCEEDED),
        ServiceAndStatus("watcher", Status.PENDING),
        ServiceAndStatus("watcher", Status.RUNNING),
        ServiceAndStatus("watcher", Status.SUCCEEDED),
    ]

    # All visited services
    visited_services = [visited.svc for visited in status_messages[-1].visited]
    assert visited_services == ["bai-client-python", "bai-bff", "fetcher-dispatcher", "executor", "watcher"]
