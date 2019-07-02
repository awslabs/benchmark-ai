from dataclasses import dataclass


@dataclass
class DataSetSizeInfo:
    total_size: int
    file_count: int
    max_size: int
