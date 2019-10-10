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

LABEL_VALIDATION_REGEX = re.compile("([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]")
INVALID_LABEL_MESSAGE = (
    f"(RegExp used for validation is ([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9] "
    f"Please use Kubernetes label syntax: "
    f"https://kubernetes.io/docs/concepts/overview/working-with-objects/labels"
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
                    f'Please use Kubernetes cron job syntax or "single_run" for non-periodic runs'
                )

        for label, value in self.info.labels.items():
            if not LABEL_VALIDATION_REGEX.fullmatch(label) or len(label) > 63:
                raise DescriptorError(f"Invalid custom label key: {label}. " + INVALID_LABEL_MESSAGE)
            if value and not LABEL_VALIDATION_REGEX.fullmatch(value) or len(value) > 63:
                raise DescriptorError(f"Invalid value for label {label}: {value} " + INVALID_LABEL_MESSAGE)

        if self.ml:
            if self.ml.framework_version and self.ml.framework == MLFramework.NONE:
                raise DescriptorError("Framework version is present, but not framework")

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


# class Descriptor:
#     """
#     The model class for a Descriptor.
#     It validates and contains all data present in the descriptor.
#     """
#
#     def __init__(self, descriptor_data: Dict, config: DescriptorConfig):
#         """
#         Constructor
#         :param descriptor_data: dict containing the data as loaded from the descriptor toml file
#         :param config: DescriptorConfig
#         """
#         self.config = config
#
#         try:
#             self.instance_type = descriptor_data["hardware"]["instance_type"]
#             self.strategy = DistributedStrategy(descriptor_data["hardware"]["strategy"])
#             self.docker_image = descriptor_data["env"]["docker_image"]
#         except ValueError as e:
#             raise DescriptorError(f"Invalid value of the field") from e
#         except KeyError as e:
#             raise DescriptorError(f"Required field is missing in the descriptor toml file: {e.args[0]}") from e
#
#         self.custom_labels = descriptor_data.get("info", {}).get("labels", {})
#         self.scheduling = descriptor_data.get("info", {}).get("scheduling", SINGLE_RUN_SCHEDULING)
#
#         self.distributed = "distributed" in descriptor_data["hardware"]
#         distributed_data = descriptor_data["hardware"].get("distributed", {})
#         self.num_instances = int(distributed_data.get("num_instances", 1))
#         processes_per_instance = distributed_data.get("processes_per_instance", "1")
#         self.gpus_per_instance = ec2_instance_info.get_instance_gpus(instance_type=self.instance_type)
#
#         def _parse_processes_per_instance(str_val: str, gpus_per_instance: int):
#             if str_val == ONE_PER_GPU:
#                 if gpus_per_instance:
#                     return gpus_per_instance
#                 else:
#                     raise DescriptorError("Requesting per-gpu process assignment on instance without gpus")
#             else:
#                 return int(str_val)
#
#         self.processes_per_instance = _parse_processes_per_instance(processes_per_instance, self.gpus_per_instance)
#
#         self.extended_shm = descriptor_data["env"].get("extended_shm", True)
#         self.privileged = descriptor_data["env"].get("privileged", False)
#
#         ml = descriptor_data.get("ml", {})
#
#         self.benchmark_code = ml.get("benchmark_code", "")
#         self.ml_args = ml.get("args", "")
#         self.framework = ml.get("framework", "")
#         self.framework_version = ml.get("framework_version", "")
#
#         self.data_sources = descriptor_data.get("data", {}).get("sources", [])
#
#         self.metrics = descriptor_data.get("output", {}).get("metrics", [])
#
#         self.zone_id = descriptor_data["hardware"].get("aws_zone_id", "")
#         self.availability_zone = descriptor_data["hardware"].get("availability_zone", "")
#
#         self.env_vars = descriptor_data.get("env", {}).get("vars", {})
#
#         self.is_inference_strategy = self.strategy == DistributedStrategy.INFERENCE
#
#         self.server = self._make_server_descriptor(descriptor_data)
#
#         self._validate()
#
#     def __eq__(self, other):
#         if isinstance(other, self.__class__):
#             return self.__dict__ == other.__dict__
#         else:
#             return False
#
#     def __ne__(self, other):
#         return not self.__eq__(other)
#
#     def is_single_run(self):
#         return self.scheduling is SINGLE_RUN_SCHEDULING
#
#     @classmethod
#     def from_toml_file(cls, toml_file: str, config: DescriptorConfig):
#         """
#         Constructor from toml file path
#         :param config: Configuration values for the descriptor
#         :param toml_file: TOML descriptor file path
#         """
#         descriptor_toml = toml.load(toml_file)
#         return Descriptor(descriptor_toml, config)
#
#     @classmethod
#     def get_server_schema(cls):
#         current_dir = os.path.dirname(os.path.abspath(__file__))
#         with open(os.path.join(current_dir, "descriptor_server_schema.json"), encoding="utf-8") as f:
#             return json.loads(f.read(), encoding="utf-8")
#
#     def _make_server_descriptor(self, descriptor_data: Dict[str, Any]):
#
#         if not self.is_inference_strategy:
#             return None
#
#         server_dict = descriptor_data.get("server", {})
#
#         # Validate against schema
#         try:
#             jsonschema.validate(
#                 server_dict, schema=Descriptor.get_server_schema(), format_checker=jsonschema.draft7_format_checker
#             )
#         except jsonschema.ValidationError as err:
#             raise DescriptorError(f"Invalid [server] definition: {err.message}") from err
#
#         return dacite.from_dict(
#             data_class=ServerDescriptor,
#             data=server_dict,
#             config=dacite.Config(
#                 type_hooks={
#                     # Convert HttpProbeScheme from str to HttpProbeScheme
#                     HttpProbeScheme: lambda scheme_str: HttpProbeScheme(scheme_str.lower())
#                 }
#             ),
#         )
#
#     def _validate(self):
#         """
#         Validates that this descriptor is valid
#         """
#         if self.strategy.value not in self.config.valid_strategies:
#           raise DescriptorError(f"Invalid strategy: {self.strategy} (must be one of {self.config.valid_strategies})")
#
#         if self.framework not in self.config.valid_frameworks:
#           raise DescriptorError(f"Invalid framework  {self.framework} (must be one of {self.config.valid_frameworks}")
