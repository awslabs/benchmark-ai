import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

import jsonschema
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
    CLIENT_SERVER = "client_server"


SINGLE_RUN_SCHEDULING = "single_run"

ONE_PER_GPU = "gpus"


class Descriptor:
    """
    The model class for a Descriptor.
    It validates and contains all data the descriptor contains.
    """

    def __init__(self, descriptor_data: Dict, config: DescriptorConfig):
        """
        Constructor
        :param descriptor_data: dict containing the data as loaded from the descriptor toml file
        :param config: DescriptorConfig
        """
        self.config = config

        try:
            self.instance_type = descriptor_data["hardware"]["instance_type"]
            self.strategy = DistributedStrategy(descriptor_data["hardware"]["strategy"])
            self.docker_image = descriptor_data["env"]["docker_image"]
        except ValueError as e:
            raise DescriptorError(f"Invalid value of the field") from e
        except KeyError as e:
            raise DescriptorError(f"Required field is missing in the descriptor toml file: {e.args[0]}") from e

        self.scheduling = descriptor_data.get("info", {}).get("scheduling", SINGLE_RUN_SCHEDULING)

        self.distributed = "distributed" in descriptor_data["hardware"]
        distributed_data = descriptor_data["hardware"].get("distributed", {})
        self.num_instances = int(distributed_data.get("num_instances", 1))
        processes_per_instance = distributed_data.get("processes_per_instance", "1")
        self.gpus_per_instance = ec2_instance_info.get_instance_gpus(instance_type=self.instance_type)

        def _parse_processes_per_instance(str_val: str, gpus_per_instance: int):
            if str_val == ONE_PER_GPU:
                if gpus_per_instance:
                    return gpus_per_instance
                else:
                    raise DescriptorError("Requesting per-gpu process assignment on instance without gpus")
            else:
                return int(str_val)

        self.processes_per_instance = _parse_processes_per_instance(processes_per_instance, self.gpus_per_instance)

        self.extended_shm = descriptor_data["env"].get("extended_shm", True)
        self.privileged = descriptor_data["env"].get("privileged", False)

        ml = descriptor_data.get("ml", {})

        self.benchmark_code = ml.get("benchmark_code", "")
        self.ml_args = ml.get("args", "")
        self.framework = ml.get("framework", "")
        self.framework_version = ml.get("framework_version", "")

        self.dataset = descriptor_data.get("data", {}).get("id", "")
        self.data_sources = descriptor_data.get("data", {}).get("sources", [])

        self.metrics = descriptor_data.get("output", {}).get("metrics", [])

        self.zone_id = descriptor_data["hardware"].get("aws_zone_id", "")
        self.availability_zone = descriptor_data["hardware"].get("availability_zone", "")

        self.env_vars = descriptor_data.get("env", {}).get("vars", {})

        self.server = descriptor_data.get("server", {})

        # set boolean defaults
        if "env" in self.server:
            self.server["env"]["privileged"] = self.server["env"].get("privileged", False)
            self.server["env"]["extended_shm"] = self.server["env"].get("extended_shm", True)

        self.is_client_server = self.strategy == DistributedStrategy.CLIENT_SERVER

        self._validate()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def is_single_run(self):
        return self.scheduling is SINGLE_RUN_SCHEDULING

    @classmethod
    def from_toml_file(cls, toml_file: str, config: DescriptorConfig):
        """
        Constructor from toml file path
        :param config: Configuration values for the descriptor
        :param toml_file: TOML descriptor file path
        """
        descriptor_toml = toml.load(toml_file)
        return Descriptor(descriptor_toml, config)

    @classmethod
    def get_server_schema(cls):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, "descriptor_server_schema.json"), encoding="utf-8") as f:
            return json.loads(f.read(), encoding="utf-8")

    def _validate(self):
        """
        Validates that this descriptor is valid
        """
        if self.strategy.value not in self.config.valid_strategies:
            raise DescriptorError(f"Invalid strategy: {self.strategy} (must be one of {self.config.valid_strategies})")

        if self.framework not in self.config.valid_frameworks:
            raise DescriptorError(f"Invalid framework  {self.framework} (must be one of {self.config.valid_frameworks}")

        if self.framework_version and not self.framework:
            raise DescriptorError("Framework version is present, but not framework")

        if self.is_client_server:
            try:
                jsonschema.validate(
                    self.server, schema=Descriptor.get_server_schema(), format_checker=jsonschema.draft7_format_checker
                )
            except jsonschema.ValidationError as err:
                raise DescriptorError(f"Invalid [server] definition: {err}") from err

        if self.distributed:
            if self.num_instances <= 1:
                logging.warning(f"Specified a distributed strategy but using {self.num_instances} nodes")

        if self.scheduling != SINGLE_RUN_SCHEDULING:
            if not CronSlices.is_valid(self.scheduling):
                raise DescriptorError(
                    f"Invalid cron expression in scheduling field: {self.scheduling}. "
                    f'Please use Kubernetes cron job syntax or "single_run" for non-periodic runs'
                )

        if not isinstance(self.ml_args, str):
            raise DescriptorError(f"Invalid type in field ml.args: it must be a string")

    def find_data_source(self, src: str):
        for source in self.data_sources:
            if source["src"] == src:
                return source
        else:
            raise DescriptorError(
                f"Could not find data source with src: {src} \n" f"Data sources are: {self.data_sources}"
            )
