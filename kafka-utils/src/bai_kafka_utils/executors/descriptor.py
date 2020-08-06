import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

import dacite
import toml
from crontab import CronSlices

from bai_kafka_utils.executors.util import ec2_instance_info


@dataclass
class DescriptorConfig:
    valid_strategies: List[str]
    valid_frameworks: List[str]


class DescriptorError(Exception):
    pass


class DistributedStrategy(Enum):
    SINGLE_NODE = "single_node"
    HOROVOD = "horovod"
    INFERENCE = "inference"


SINGLE_RUN_SCHEDULING = "single_run"

ONE_PER_GPU = "gpus"

LABEL_VALIDATION_REGEX = re.compile("(?=.{1,63}$)([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]")
INVALID_LABEL_MESSAGE = (
    "(RegExp used for validation is ([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9] "
    "Please use Kubernetes label syntax: "
    "https://kubernetes.io/docs/concepts/overview/working-with-objects/labels"
)


class HttpProbeScheme(Enum):
    HTTP = "http"
    HTTPS = "https"


class ExecutionEngine(Enum):
    DEFAULT = "default"
    SAGEMAKER = "aws.sagemaker"


class MLFramework(Enum):
    TENSORFLOW = "tensorflow"
    MXNET = "mxnet"
    NONE = ""


@dataclass
class MLScript:
    script: str


@dataclass
class InfoDescriptor:
    description: str
    task_name: Optional[str] = None
    execution_engine: Optional[ExecutionEngine] = ExecutionEngine.DEFAULT
    scheduling: Optional[str] = SINGLE_RUN_SCHEDULING
    labels: Optional[Dict[str, str]] = field(default_factory=dict)


@dataclass
class MLDescriptor:
    framework: MLFramework = MLFramework.NONE
    benchmark_code: Optional[str] = None
    args: Optional[str] = None
    framework_version: Optional[str] = None
    script: Optional[MLScript] = None


@dataclass
class CustomParamsDescriptor:
    python_version: Optional[str] = None
    sagemaker_job_name: Optional[str] = None
    enable_sagemaker_metrics: Optional[bool] = None
    hyper_params: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class HttpProbeDescriptor:
    path: str
    port: Optional[int] = None
    scheme: Optional[HttpProbeScheme] = HttpProbeScheme.HTTP
    initial_delay_seconds: Optional[int] = 10
    period_seconds: Optional[int] = 10
    timeout_seconds: Optional[int] = 1
    success_threshold: Optional[int] = 1
    failure_threshold: Optional[int] = 3


@dataclass
class MetricDescriptor:
    name: str
    units: str
    pattern: str


@dataclass
class OutputDescriptor:
    metrics: List[MetricDescriptor]


@dataclass
class DownloadableContent:
    src: str
    path: str
    id: Optional[str] = None
    md5: Optional[str] = None


@dataclass
class HardwareDescriptor:
    instance_type: str
    gpus_per_instance: int = field(init=False)
    aws_zone_id: Optional[str] = None
    availability_zone: Optional[str] = None

    def __post_init__(self):
        self.gpus_per_instance = ec2_instance_info.get_instance_gpus(self.instance_type)


@dataclass
class BenchmarkDistributedHardwareDescriptor:
    num_instances: int = 2
    processes_per_instance: str = "1"


@dataclass
class BenchmarkHardwareDescriptor(HardwareDescriptor):
    strategy: DistributedStrategy = DistributedStrategy.SINGLE_NODE

    # Only meaningful for horovod or other future multi-node strategies
    distributed: BenchmarkDistributedHardwareDescriptor = field(default_factory=BenchmarkDistributedHardwareDescriptor)

    # TODO: We should probably refactor this and make it into a member function
    # This is here just to convert "ONE_PER_GPU" into the number of processes per instance
    processes_per_instance: int = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        if self.distributed:
            if self.distributed.processes_per_instance == ONE_PER_GPU:
                if self.gpus_per_instance:
                    self.processes_per_instance = self.gpus_per_instance
                else:
                    raise DescriptorError("Requesting per-gpu process assignment on instance without gpus")
            else:
                self.processes_per_instance = int(self.distributed.processes_per_instance)


@dataclass
class ServerEnvDescriptor:
    # required
    docker_image: str
    ports: List[int]
    start_command: str

    # optional
    privileged: bool = False
    extended_shm: bool = True
    vars: Dict[str, str] = field(default_factory=dict)
    readiness_probe: Optional[HttpProbeDescriptor] = None
    start_command_args: Optional[str] = None


@dataclass
class ServerDescriptor:
    hardware: HardwareDescriptor
    env: ServerEnvDescriptor
    models: Optional[List[DownloadableContent]] = field(default_factory=list)
    output: Optional[OutputDescriptor] = None


@dataclass
class BenchmarkEnvDescriptor:
    docker_image: str

    # Optional
    privileged: bool = False
    extended_shm: bool = True
    vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class BenchmarkDataDescriptor:
    sources: List[DownloadableContent]


@dataclass
class BenchmarkDescriptor:
    spec_version: str
    info: InfoDescriptor
    hardware: BenchmarkHardwareDescriptor
    env: BenchmarkEnvDescriptor
    output: Optional[OutputDescriptor] = None
    ml: Optional[MLDescriptor] = None
    data: Optional[BenchmarkDataDescriptor] = None
    custom_params: Optional[CustomParamsDescriptor] = None
    # required under inference strategy
    server: Optional[ServerDescriptor] = None

    def __post_init__(self):

        if self.hardware.strategy == DistributedStrategy.INFERENCE and not self.server:
            raise DescriptorError("Missing server definition")

        if self.hardware.strategy in [DistributedStrategy.HOROVOD] and not self.hardware.distributed:
            raise DescriptorError("Missing distributed hardware definition")

        if self.hardware.distributed:
            if self.hardware.distributed.num_instances <= 1:
                logging.warning(
                    f"Specified a distributed strategy but using {self.hardware.distributed.num_instances} nodes"
                )
                raise DescriptorError(f"Invalid number of instances {self.hardware.distributed.num_instances}")

        if self.info.scheduling != SINGLE_RUN_SCHEDULING:
            if not CronSlices.is_valid(self.info.scheduling):
                raise DescriptorError(
                    f"Invalid cron expression in scheduling field: {self.info.scheduling}. "
                    'Please use Kubernetes cron job syntax or "single_run" for non-periodic runs'
                )

        for label, value in self.info.labels.items():
            if not LABEL_VALIDATION_REGEX.fullmatch(label):
                raise DescriptorError(f"Invalid custom label key: {label}. " + INVALID_LABEL_MESSAGE)
            if value and not LABEL_VALIDATION_REGEX.fullmatch(value):
                raise DescriptorError(f"Invalid value for label {label}: {value} " + INVALID_LABEL_MESSAGE)

        if self.ml:
            if self.ml.framework_version and self.ml.framework == MLFramework.NONE:
                raise DescriptorError("Framework version is present, but not framework")
            if self.ml.script and not self.ml.script.script.endswith(".tar"):
                raise DescriptorError(
                    f"Script mode section is present, but script file: {self.ml.script.script} is not a tar file"
                )

    @classmethod
    def from_dict(cls, descriptor_dict: Dict[str, Any], config: DescriptorConfig = None):
        try:
            descriptor = dacite.from_dict(
                data_class=BenchmarkDescriptor,
                data=descriptor_dict,
                config=dacite.Config(
                    type_hooks={
                        DistributedStrategy: lambda dist_strat: DistributedStrategy(dist_strat),
                        ExecutionEngine: lambda exec_eng: ExecutionEngine(exec_eng),
                        MLFramework: lambda framework: MLFramework(framework),
                        HttpProbeScheme: lambda scheme_str: HttpProbeScheme(scheme_str.lower()),
                    },
                    strict=True,
                ),
            )
            if config:
                if descriptor.hardware.strategy.value not in config.valid_strategies:
                    raise DescriptorError(
                        f"Invalid strategy: {descriptor.hardware.strategy} (must be one of {config.valid_strategies})"
                    )

                if descriptor.ml.framework.value not in config.valid_frameworks:
                    raise DescriptorError(
                        f"Invalid framework  {descriptor.ml.framework} (must be one of {config.valid_frameworks}"
                    )
            return descriptor
        except (dacite.MissingValueError, dacite.WrongTypeError, ValueError) as err:
            raise DescriptorError(f"Error parsing descriptor: {err}")

    @classmethod
    def from_toml(cls, toml_file: str, config: DescriptorConfig = None):
        descriptor_dict = toml.load(toml_file)
        return BenchmarkDescriptor.from_dict(descriptor_dict, config)

    def is_single_run(self):
        return self.info.scheduling is SINGLE_RUN_SCHEDULING

    def is_inference_strategy(self):
        return self.hardware.strategy == DistributedStrategy.INFERENCE
