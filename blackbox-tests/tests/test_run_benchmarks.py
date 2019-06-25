import os
import sys
from builtins import TimeoutError
from contextlib import contextmanager

import subprocess
import tempfile

from bai_kafka_utils.events import Status
from typing import Iterable, Iterator
from collections import namedtuple
from pathlib import Path
from bai_client.client import BaiClient
import datetime
import time
import pytest


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
            port_forward_process.kill()


StatusInfo = namedtuple("StatusInfo", ("message_id", "status", "message", "service"))


def generate_status_infos(
    bai_client,
    action_id,
    *,
    sleep_between_status_checks=datetime.timedelta(milliseconds=500),
    timeout=datetime.timedelta(minutes=10),
    callback_on_every_status_check=lambda: None,
) -> Iterator[StatusInfo]:
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
        status_events = bai_client.status(action_id)
        callback_on_every_status_check()

        status_infos = [
            StatusInfo(event.message_id, event.status, event.message, event.visited[-1].svc) for event in status_events
        ]
        if len(status_infos) == 0:
            continue

        status_infos_to_print = status_infos[index_of_last_status:]
        for status_info in status_infos_to_print:
            yield status_info
        index_of_last_status = len(status_infos)
        time.sleep(sleep_between_status_checks.total_seconds())
    else:
        raise TimeoutError()


def wait_for_benchmark_completion(bai_client, action_id):
    def print_progress():
        sys.stdout.write(".")

    status_events = generate_status_infos(bai_client, action_id, callback_on_every_status_check=print_progress)
    for status_info in status_events:
        print()
        print(f"Benchmark Status: [{status_info.service}] - {status_info.status}: {status_info.message}")
        if status_info.service == "watcher" and status_info.status in [Status.FAILED, Status.SUCCEEDED]:
            print(f"Benchmark finished: {status_info.status}")
            return
        sys.stdout.flush()


def _wait_for_benchmark_completion(bai_client, action_id, sleep_seconds_between_status_checks=0.5):
    deadline = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    index_of_last_printed_status = 0
    while deadline > datetime.datetime.utcnow():
        status_events = bai_client.status(action_id)
        status_infos = [
            StatusInfo(event.message_id, event.status, event.message, event.visited[-1].svc) for event in status_events
        ]
        if len(status_infos) == 0:
            print("No status yet available")
        else:
            last_status_info = status_infos[-1]
            if last_status_info.service == "watcher" and last_status_info.status in [Status.FAILED, Status.SUCCEEDED]:
                print(f"Benchmark finished: {last_status_info.status}")
                return
            status_infos_to_print = status_infos[index_of_last_printed_status:]
            if len(status_infos_to_print) == 0:
                sys.stdout.write(".")
            else:
                print()
                for status_info in status_infos_to_print:
                    print(f"Benchmark Status: [{status_info.service}] - {status_info.status}: {status_info.message}")
                index_of_last_printed_status = len(status_infos)
        time.sleep(sleep_seconds_between_status_checks)
    else:
        raise ValueError("Benchmark didn't finish")


ServiceAndStatus = namedtuple("T", ("visited_service", "status"))


def unique(objects: Iterable) -> Iterable:
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
        status_events = client.status(action_id)
    print("#" * 120)
    print("# Status events (for debugging)")
    print("#" * 120)
    print(status_events)

    visited_services = [event.visited[-1].svc for event in status_events]
    status_values = [event.status for event in status_events]

    events = (ServiceAndStatus(*tuple) for tuple in zip(visited_services, status_values))
    events = unique(events)
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
    visited_services = [visited.svc for visited in status_events[-1].visited]
    assert visited_services == ["bai-client-python", "bai-bff", "fetcher-dispatcher", "executor", "watcher"]
