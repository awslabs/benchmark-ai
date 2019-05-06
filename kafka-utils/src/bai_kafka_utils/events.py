from dataclasses import dataclass

from dataclasses_json import dataclass_json
from typing import Dict, List, Optional, Type, Any


@dataclass_json
@dataclass
class DataSet:
    src: str
    md5: Optional[str] = None
    dst: Optional[str] = None


@dataclass_json
@dataclass
class BenchmarkDoc:
    # descriptor_filename: str
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
class ExecutorPayload(BenchmarkPayload):
    job: BenchmarkJob


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
    payload: BenchmarkPayload


def __make_benchmark_event(payload_type: Type[BenchmarkPayload]):
    @dataclass_json
    @dataclass
    class BenchmarkEventWithPayload(BenchmarkEvent):
        payload: payload_type

    return BenchmarkEventWithPayload


FetcherBenchmarkEvent = __make_benchmark_event(FetcherPayload)

ExecutorBenchmarkEvent = __make_benchmark_event(ExecutorPayload)
