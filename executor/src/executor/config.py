from dataclasses import dataclass

from transpiler.config import DescriptorConfig, BaiConfig, EnvironmentInfo


@dataclass
class ExecutorConfig:
    descriptor: str
    filename: str
    kubeconfig: str
    descriptor_config: DescriptorConfig
    bai_config: BaiConfig
    environment_info: EnvironmentInfo
