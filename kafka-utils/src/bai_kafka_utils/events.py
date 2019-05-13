import dataclasses
from enum import Enum

import dacite

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import List, Optional, Type, Dict, Any, TypeVar


@dataclass_json
@dataclass
class DataSet:
    src: str
    md5: Optional[str] = None
    dst: Optional[str] = None


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
    def create_from_fetcher_payload(cls, payload: FetcherPayload, job: BenchmarkJob):
        return create_from_object(ExecutorPayload, payload, job=job)


@dataclass_json
@dataclass
class VisitedService:
    svc: str
    tstamp: int
    version: str
    node: Optional[str] = None


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


@dataclass_json
@dataclass
class FetcherBenchmarkEvent(BenchmarkEvent):
    payload: FetcherPayload


@dataclass_json
@dataclass
class ExecutorBenchmarkEvent(BenchmarkEvent):
    payload: ExecutorPayload


class Status(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    ERROR = "ERROR"
    INITIALIZING = "INITIALIZING"
    SUCCEEDED = "SUCCEEDED"
    SUBMITTED = "SUBMITTED"


@dataclass_json
@dataclass
class StatusMessageBenchmarkEvent(BenchmarkEvent):
    """
    Status events represent what the user will receive as the status of their benchmark.

    The messages should be thought to be "user-friendly" as to give insight to the user on what is happening inside BAI
    regarding her benchmark.
    """

    message: str
    status: Status
    payload: Any

    @classmethod
    def create_from_event(cls, status: Status, message: str, event: BenchmarkEvent):
        return create_from_object(StatusMessageBenchmarkEvent, event, message=message, status=status)


T = TypeVar("T")


def create_from_object(desired_class: Type[T], source_object, **overriden_fields) -> T:
    if not dataclasses.is_dataclass(desired_class):
        raise ValueError("Desired class is not a dataclass type, its type is {}".format(desired_class))
    if not dataclasses.is_dataclass(source_object):
        raise ValueError("Source object is not a dataclass type, its type is {}".format(type(source_object)))
    data = dataclasses.asdict(source_object)
    data.update(overriden_fields)
    return dacite.from_dict(data_class=desired_class, data=data)
