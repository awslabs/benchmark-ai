from dataclasses import dataclass
from enum import Enum

from dataclasses_json import dataclass_json

DEFAULT_ENCODING = "utf-8"


class FetcherStatus(Enum):
    def __new__(cls, val: str, final: bool):
        obj = object.__new__(cls)
        obj._value_ = val
        obj.final = final
        return obj

    PENDING = "PENDING", False
    RUNNING = "RUNNING", False
    DONE = "DONE", True
    FAILED = "FAILED", True


@dataclass
@dataclass_json
class FetcherResult:
    status: FetcherStatus
    message: str = None

    def to_binary(self):
        return self.to_json().encode(DEFAULT_ENCODING)

    @classmethod
    def from_binary(cls, bin_data):
        return FetcherResult.from_json(bin_data.decode(DEFAULT_ENCODING))
