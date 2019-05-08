import copy
import dataclasses

from dacite import from_dict
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import List, Optional, Type, Dict, Any


@dataclass_json
@dataclass
class DataSet:
    src: str
    md5: Optional[str] = None
    dst: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None


@dataclass_json
@dataclass
class BenchmarkDoc:
    contents: Dict[str, Any]
    doc: str
    sha1: str
    descriptor_filename: Optional[str] = None
    verified: Optional[bool] = False


@dataclass_json
@dataclass
class BenchmarkJob:
    id: str
    status: str
    k8s_yaml: str
    output: Optional[str] = None


@dataclass_json
@dataclass
class BenchmarkPayload:
    toml: BenchmarkDoc


@dataclass_json
@dataclass
class FetcherPayload(BenchmarkPayload):
    datasets: List[DataSet]


@dataclass_json
@dataclass
class ExecutorPayload(FetcherPayload):
    job: BenchmarkJob

    @classmethod
    def from_fetcher_payload(cls, payload, job: BenchmarkJob):
        payload_as_dict = dataclasses.asdict(copy.deepcopy(payload))
        payload_as_dict["job"] = job
        return from_dict(data_class=ExecutorPayload, data=payload_as_dict)


@dataclass_json
@dataclass
class VisitedService:
    svc: str
    tstamp: int
    version: str


@dataclass_json
@dataclass
class BenchmarkEvent:
    action_id: str
    message_id: str
    client_id: str
    client_version: str
    client_username: str
    authenticated: bool
    tstamp: int
    visited: List[VisitedService]
    payload: Any

    @classmethod
    def from_event_new_payload(cls, benchmark_event, payload: BenchmarkPayload):
        return dataclasses.replace(benchmark_event, payload=payload)


def __make_benchmark_event(payload_type: Type):
    @dataclass_json
    @dataclass
    class BenchmarkEventWithPayload(BenchmarkEvent):
        payload: payload_type

    return BenchmarkEventWithPayload


@dataclass
@dataclass_json
class StatusMessagePayload:
    message: str


FetcherBenchmarkEvent = __make_benchmark_event(FetcherPayload)

ExecutorBenchmarkEvent = __make_benchmark_event(ExecutorPayload)

StatusMessageBenchmarkEvent = __make_benchmark_event(StatusMessagePayload)
