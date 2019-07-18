from dataclasses import dataclass, field
from typing import List

from transpiler.config import BaiConfig, EnvironmentInfo
from transpiler.descriptor import DescriptorConfig


@dataclass
class ExecutorConfig:
    # TODO: Create a transpilerConfig with the fields below, we shouldnt be passing
    # information such as kubectl to the transpiler
    descriptor_config: DescriptorConfig
    bai_config: BaiConfig
    environment_info: EnvironmentInfo
    kubectl: str
    valid_execution_engines: List[str] = field(default_factory=list)
