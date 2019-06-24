import os

import subprocess
import tempfile

from bai_kafka_utils.events import Status
from typing import Iterable
from collections import namedtuple
from pathlib import Path
from bai_client.client import BaiClient
import datetime
import time
import pytest


@pytest.fixture(scope="module")
def client():
    # HACK: Port forwarding because BFF is not currently exposed to the world as a service
    #       https://github.com/MXNetEdge/benchmark-ai/issues/454
    import sys

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
                    print(port_forward_process.stdout.read())
                    raise ValueError(f"Port-forward command returned with exitcode: {retcode}")
                line = port_forward_process.stdout.readline()
                line = line.decode("utf-8")
                print(line)
                if "Forwarding from 127.0.0.1:8080 -> 8080" in line:
                    break
            yield BaiClient(endpoint="http://localhost:8080")


StatusInfo = namedtuple("StatusInfo", ("message_id", "status", "message", "service"))


def wait_for_benchmark_completion(bai_client, action_id, sleep_seconds_between_status_checks=0.5):
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
            for i in range(index_of_last_printed_status, len(status_infos)):
                status_info = status_infos[i]
                print(f"Benchmark Status: [{status_info.service}] - {status_info.status}: {status_info.message}")
            index_of_last_printed_status = len(status_infos)
        time.sleep(sleep_seconds_between_status_checks)
    else:
        raise ValueError("Benchmark didn't finish")


ServiceAndStatus = namedtuple("T", ("visited_service", "status"))


def remove_repeated_events(events: Iterable[ServiceAndStatus]) -> Iterable[ServiceAndStatus]:
    last = None
    for event in events:
        if last is not None and event == last:
            continue
        yield event
        last = event


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
    action_id = client.submit(str(get_sample_benchmark_descriptor_filepath(descriptor_filename)))
    print(f"action_id={action_id}")

    wait_for_benchmark_completion(client, action_id)

    status_events = client.status(action_id)
    print(status_events)  # To aid debugging
    visited_services = [event.visited[-1].svc for event in status_events]
    status_values = [event.status for event in status_events]

    events = (ServiceAndStatus(*tuple) for tuple in zip(visited_services, status_values))
    events = remove_repeated_events(events)
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
