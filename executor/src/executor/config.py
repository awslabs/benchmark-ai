from dataclasses import dataclass

from transpiler.config import DescriptorConfig, BaiConfig, EnvironmentInfo


@dataclass
class ExecutorConfig:
    kubectl: str
    # TODO: Create a transpilerConfig with the fields below, we shouldnt be passing
    # information such as kubectl to the transpiler
    descriptor_config: DescriptorConfig
    bai_config: BaiConfig
    environment_info: EnvironmentInfo
