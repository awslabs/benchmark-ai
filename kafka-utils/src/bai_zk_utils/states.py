from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json

from bai_kafka_utils.events import FetcherStatus, FetchedType

DEFAULT_ENCODING = "utf-8"


@dataclass
@dataclass_json
class FetcherResult:
    status: FetcherStatus
    type: Optional[FetchedType] = None
    message: Optional[str] = ""

    def to_binary(self):
        return self.to_json().encode(DEFAULT_ENCODING)

    @classmethod
    def from_binary(cls, bin_data):
        return FetcherResult.from_json(bin_data.decode(DEFAULT_ENCODING))
