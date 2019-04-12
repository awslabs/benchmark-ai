from dataclasses import dataclass

from dataclasses_json import dataclass_json
from typing import Dict, List, Optional


@dataclass_json
@dataclass
class DataSet:
    src: str
    md5: str = None
    dst: str = None


@dataclass_json
@dataclass
class BenchmarkDoc:
    doc: str
    md5: str
    data: Dict


@dataclass_json
@dataclass
class BenchmarkPayload:
    toml: BenchmarkDoc
    data_sets: Optional[List[DataSet]]


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
    payload: BenchmarkPayload
