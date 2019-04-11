from dataclasses import dataclass

from dataclasses_json import dataclass_json
from typing import Dict


@dataclass_json
@dataclass
class BenchmarkDoc:
    doc: str
    md5: str
    data: Dict
