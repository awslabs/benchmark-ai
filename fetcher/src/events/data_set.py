from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class DataSet:
    src: str
    md5: str = None
    dst: str = None
