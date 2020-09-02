#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Type, Dict, Any, TypeVar, Union

import dacite
from dataclasses_json import dataclass_json

_REQUIRED = object()


class FetcherStatus(Enum):
    def __new__(cls, val: str, final: bool, success: bool):
        obj = object.__new__(cls)
        obj._value_ = val
        obj.final = final
        obj.success = success
        return obj

    PENDING = "PENDING", False, False
    RUNNING = "RUNNING", False, False
    DONE = "DONE", True, True
    FAILED = "FAILED", True, False
    CANCELED = "CANCELED", True, False

    def __str__(self):
        return self.value


class FetchedType(Enum):
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"

    def __str__(self):
        return self.value


@dataclass_json
@dataclass
class ContentSizeInfo:
    total_size: int
    file_count: int
    max_size: int


@dataclass_json
@dataclass
class DownloadableContent:
    # Set by the user
    src: str  # uri of the data
    path: str  # filesystem path where data will be found in the benchmark pod
    id: Optional[str] = None  # (Opt) content id
    md5: Optional[str] = None  # (Opt) content md5

    # Set by the fetcher
    dst: Optional[str] = None  # internal location of the data
    type: Optional[FetchedType] = None
    status: Optional[FetcherStatus] = None
    message: Optional[str] = None
    size_info: Optional[ContentSizeInfo] = None


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
    output: Optional[str] = None
    extras: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclass_json
@dataclass
class BenchmarkPayload:
    toml: BenchmarkDoc


@dataclass_json
@dataclass
class FileSystemObject(object):
    dst: str


@dataclass_json
@dataclass
class FetcherPayload(BenchmarkPayload):
    datasets: List[DownloadableContent]
    models: List[DownloadableContent] = dataclasses.field(default_factory=list)
    scripts: List[FileSystemObject] = dataclasses.field(default_factory=list)


@dataclass_json
@dataclass(init=False)
class ExecutorPayload(FetcherPayload):
    # This ugly constructor enables default behaviour on FetcherPayload.scripts
    def __init__(
        self,
        toml: BenchmarkDoc,
        datasets: List[DownloadableContent],
        job: BenchmarkJob,
        models: List[DownloadableContent] = None,
        scripts: List[FileSystemObject] = None,
    ):
        self.toml = toml
        self.datasets = datasets
        self.models = models or []
        self.scripts = scripts or []
        self.job = job

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
    action_id: str = _REQUIRED
    parent_action_id: Optional[str] = None
    message_id: str = _REQUIRED
    client_id: str = _REQUIRED
    client_version: str = _REQUIRED
    client_username: str = _REQUIRED
    authenticated: bool = _REQUIRED
    tstamp: int = _REQUIRED
    visited: List[VisitedService] = _REQUIRED
    type: str = _REQUIRED
    payload: Any = _REQUIRED

    def __post_init__(self):
        # We cannot add BenchmarkEvent.parent_action_id as an optional with default value
        # as this breaks the sub-classes. Therefore, we attach default values
        # to all fields and simulate the required fields.
        for field in self.__dict__.keys():
            if self.__dict__[field] == _REQUIRED:
                raise TypeError(f"__init__ missing 1 required argument: '{field}'")


@dataclass_json
@dataclass
class FetcherBenchmarkEvent(BenchmarkEvent):
    payload: FetcherPayload


@dataclass_json
@dataclass
class ExecutorBenchmarkEvent(BenchmarkEvent):
    payload: ExecutorPayload


@dataclass_json
@dataclass
class CommandRequestPayload:
    command: str
    args: Union[Dict[str, str], List[str]] = None


@dataclass_json
@dataclass
class CommandRequestEvent(BenchmarkEvent):
    payload: CommandRequestPayload


@dataclass_json
@dataclass
class CommandResponsePayload:
    return_code: int
    message: str
    cmd_submit: CommandRequestEvent
    return_value: Optional[Any] = None


@dataclass_json
@dataclass
class CommandResponseEvent(BenchmarkEvent):
    payload: CommandResponsePayload = _REQUIRED

    def __post_init__(self):
        # We cannot add BenchmarkEvent.parent_action_id as an optional with default value
        # as this breaks the sub-classes. Therefore, we attach default values
        # to all fields and simulate the required fields.
        for field in self.__dict__.keys():
            if self.__dict__[field] == _REQUIRED:
                raise TypeError(f"__init__ missing 1 required argument: '{field}'")


class Status(Enum):
    """
    The items of this Status enum translate into the status of the job of a specific "sub-section" of the pipeline.

    For example: (this is not supposed to be a documentation on how services are behaving, it's just an example)

        Let's say the full pipeline for jobs look like this:

            BFF => Fetcher => Executor => Watcher

        Then user "Joe" submits a benchmark:

            => First service: `BFF`

            1.1 - starts processing the request:
                    - sends the status message: PENDING
            1.2 - done processing the request
                    - sends the status message: SUCCEEDED

            => Next service: `Fetcher`

            2.1 - starts processing the request:
                    - sends the status message: PENDING
            2.2 - done downloading all files:
                    - sends the status message: SUCCEEDED

            => Next service: `Executor`

            3.1 - starts processing the request:
                    - sends the status message: PENDING
            3.2 - done processing the request:
                    - sends the status message: SUCCEEDED

            => Next service: `Watcher`

            4.1 - starts processing the request:
                    - sends the status message: PENDING
            4.2 - notices that Kubernetes needs to spawn nodes:
                    - sends the status message: INITIALIZING
            4.3 - notices that the Pods are all executing the `init` containers:
                    - sends the status message: INITIALIZING
            4.4 - notices that the benchmark container at the Pods are all running:
                    - sends the status message: RUNNING
            4.5 - done processing the request:
                    - sends the status message: SUCCEEDED

    As can be noticed, each "service" will have its own notion of what each of these STATUS values mean.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    ERROR = "ERROR"
    INITIALIZING = "INITIALIZING"
    SUCCEEDED = "SUCCEEDED"
    CANCELED = "CANCELED"
    METRICS_AVAILABLE = "METRICS AVAILABLE"


@dataclass_json
@dataclass
class StatusMessageBenchmarkEventPayload:
    message: str
    status: Status
    src_event: Optional[BenchmarkEvent] = None


@dataclass_json
@dataclass
class StatusMessageBenchmarkEvent(BenchmarkEvent):
    """
    Status events represent what the user will receive as the status of their benchmark.

    The messages should be thought to be "user-friendly" as to give insight to the user on what is happening inside BAI
    regarding her benchmark.
    """

    payload: StatusMessageBenchmarkEventPayload = _REQUIRED

    def __post_init__(self):
        # We cannot add BenchmarkEvent.parent_action_id as an optional with default value
        # as this breaks the sub-classes. Therefore, we attach default values
        # to all fields and simulate the required fields.
        for field in self.__dict__.keys():
            if self.__dict__[field] == _REQUIRED:
                raise TypeError(f"__init__ missing 1 required argument: '{field}'")

    @classmethod
    def create_from_event(cls, status: Status, message: str, event: BenchmarkEvent):
        payload = StatusMessageBenchmarkEventPayload(message=message, status=status, src_event=event)
        return create_from_object(StatusMessageBenchmarkEvent, event, payload=payload, visited=[])


@dataclass_json
@dataclass
class MetricsEvent:
    name: str
    # When an argument is annotated as having type float, an argument of type int is acceptable
    # https://www.python.org/dev/peps/pep-0484/#id27
    value: float
    timestamp: int
    labels: Optional[Dict[str, str]] = None


T = TypeVar("T")


def create_from_object(desired_class: Type[T], source_object, **overriden_fields) -> T:
    if not dataclasses.is_dataclass(desired_class):
        raise ValueError("Desired class is not a dataclass type, its type is {}".format(desired_class))
    if not dataclasses.is_dataclass(source_object):
        raise ValueError("Source object is not a dataclass type, its type is {}".format(type(source_object)))
    data = dataclasses.asdict(source_object)
    data.update(overriden_fields)
    try:
        return dacite.from_dict(data_class=desired_class, data=data)
    except dacite.WrongTypeError as e:
        raise ValueError from e


def get_topic_event_type(topic: str):
    topic_to_event_type = {
        "BAI_APP_BFF": FetcherBenchmarkEvent,
        "BAI_APP_FETCHER": FetcherBenchmarkEvent,
        "BAI_APP_EXECUTOR": ExecutorBenchmarkEvent,
        "BAI_APP_STATUS": StatusMessageBenchmarkEvent,
        "CMD_SUBMIT": CommandRequestEvent,
        "CMD_RETURN": CommandResponseEvent,
        "BAI_METRICS": MetricsEvent,
    }
    return topic_to_event_type[topic]
