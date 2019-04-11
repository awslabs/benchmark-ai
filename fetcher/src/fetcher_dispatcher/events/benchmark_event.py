from dataclasses import dataclass

from dataclasses_json import dataclass_json

from fetcher_dispatcher.events.benchmark_payload import BenchmarkPayload
from fetcher_dispatcher.events.visited_service import VisitedService


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
    visited: [VisitedService]
    payload: BenchmarkPayload
