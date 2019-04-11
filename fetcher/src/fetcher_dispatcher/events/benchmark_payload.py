from dataclasses import dataclass

from dataclasses_json import dataclass_json
from typing import List, Optional

from fetcher_dispatcher.events.benchmark_doc import BenchmarkDoc
from fetcher_dispatcher.events.data_set import DataSet


@dataclass_json
@dataclass
class BenchmarkPayload:
    toml: BenchmarkDoc
    data_sets: Optional[List[DataSet]]
