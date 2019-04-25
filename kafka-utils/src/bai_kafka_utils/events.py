from dataclasses import dataclass

from dataclasses_json import dataclass_json
from typing import Dict, List, Optional, Type


@dataclass_json
@dataclass
class DataSet:
    src: str
    md5: Optional[str] = None
    dst: Optional[str] = None


@dataclass_json
@dataclass
class BenchmarkDoc:
    contents: Dict[str, str]
    doc: str
    md5: str


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
    data_sets: List[DataSet]


@dataclass_json
@dataclass
class ExecutorPayload(BenchmarkPayload):
    job: BenchmarkJob


@dataclass_json
@dataclass
class VisitedService:
    service: str
    timestamp: int
    version: str


@dataclass_json
@dataclass
class BenchmarkEvent:
    request_id: str
    message_id: str
    client_id: str
    client_version: str
    client_user: str
    authenticated: bool
    date: int
    visited: List[VisitedService]
    payload: Type[BenchmarkPayload]


def make_benchmark_event(payload_type: Type[BenchmarkPayload]):
    @dataclass_json
    @dataclass
    class BenchmarkEventWithPayload(BenchmarkEvent):
        payload: payload_type
    return BenchmarkEventWithPayload
