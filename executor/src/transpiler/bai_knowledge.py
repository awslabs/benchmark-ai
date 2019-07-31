import logging
import os
import random
import shlex
from dataclasses import dataclass

from bai_kafka_utils.events import DataSet, BenchmarkEvent, FileSystemObject
from bai_kafka_utils.executors.descriptor import DescriptorError, Descriptor, SINGLE_RUN_SCHEDULING, DistributedStrategy
from ruamel import yaml
from typing import List, Dict

from executor import SERVICE_NAME
from executor.config import ExecutorConfig
from transpiler.config import BaiConfig, BaiDataSource, EnvironmentInfo, BaiScriptSource
from transpiler.kubernetes_spec_logic import ConfigTemplate, VolumeMount, Volume, EmptyDirVolumeSource

SCRIPT_UNPACK_MODIFICATOR = "unpack_in_place"

SCRIPT_PULLER_CHMOD = 777

BENCHMARK_CONTAINER = "benchmark"
DATA_PULLER_CONTAINER = "data-puller"
DATASETS_VOLUME_NAME = "datasets-volume"
SCRIPTS_VOLUME_NAME = "scripts-volume"
SCRIPTS_PULLER_CONTAINER = "script-puller"

# To make things easier it's the same path in puller and benchmark
SCRIPTS_MOUNT_PATH = "/bai/scripts"

SHARED_MEMORY_VOLUME = "dshm"
SHARED_MEMORY_VOLUME_MOUNT = "/dev/shm"


@dataclass
class PullerDataSource:
    name: str
    puller_path: str


logger = logging.getLogger(__name__)


class BaiKubernetesObjectBuilder:
    """
    Adds the logic required from BAI into the Kubernetes root object that represents
    launching a benchmark.
    """

    def __init__(
        self,
        descriptor: Descriptor,
        config: BaiConfig,
        data_sources: List[BaiDataSource],
        scripts: List[BaiScriptSource],
        config_template: ConfigTemplate,
        job_id: str,
        *,
        event: BenchmarkEvent,
        environment_info: EnvironmentInfo,
        random_object: random.Random = None,
    ):
        """
        Reads the values from the descriptor file into a settings dictionary
        :param descriptor: Descriptor object with the information from the TOML
        :param config_template: The YAML template
        :param random_object: An instance of random.Random [optional].
                              This field exists mostly to facilitate testing so that predictable random data is
                              generated.
        """
        self.descriptor = descriptor
        self.config = config
        self.job_id = job_id.lower()  # Let's make it lower case - k8s complains about upper case chars

        # Using a random AZ is good enough for now
        availability_zone = self.choose_availability_zone(descriptor, environment_info, random_object)

        config_template.feed({"descriptor": descriptor})
        config_template.feed({"config": config})
        config_template.feed({"event": event})
        config_template.feed({"service_name": SERVICE_NAME})
        config_template.feed({"job_id": self.job_id})
        config_template.feed({"availability_zone": availability_zone})

        self.internal_env_vars = {}

        self.root = config_template.build()
        self.add_data_volume_mounts(data_sources)
        self.add_scripts(scripts)
        self.add_shared_memory()
        self.add_env_vars()

        if self.config.suppress_job_affinity:
            self.root.remove_affinity()

        if descriptor.scheduling != SINGLE_RUN_SCHEDULING:
            self.root.to_cronjob(descriptor.scheduling)

    @staticmethod
    def choose_availability_zone(
        descriptor: Descriptor, environment_info: EnvironmentInfo, random_object: random.Random = None
    ):
        if descriptor.availability_zone:
            if descriptor.availability_zone in environment_info.availability_zones.values():
                return descriptor.availability_zone
            raise DescriptorError(f"Invalid zone name {descriptor.availability_zone}")
        # Try to find the zone id
        if descriptor.zone_id:
            if descriptor.zone_id in environment_info.availability_zones:
                return environment_info.availability_zones[descriptor.zone_id]
            raise DescriptorError(f"Invalid zone id {descriptor.zone_id}")

        if random_object is None:
            random_object = random.Random()

        return random_object.choice(list(environment_info.availability_zones.values()))

    def add_data_volume_mounts(self, data_sources):
        benchmark_container = self.root.find_container(BENCHMARK_CONTAINER)
        data_mounts = self._get_data_mounts(data_sources)
        self._update_data_puller(data_mounts, data_sources)
        benchmark_container.volumeMounts.extend(self._get_container_volume_mounts(data_mounts))

    def add_shared_memory(self):
        if self.descriptor.extended_shm:
            self._add_extended_shm()

    def _add_extended_shm(self):
        pod_spec_volumes = self.root.get_pod_spec().volumes
        container_volume_mounts = self.root.find_container(BENCHMARK_CONTAINER).volumeMounts

        shared_memory_vol = SHARED_MEMORY_VOLUME

        shm_vol = Volume(name=shared_memory_vol, emptyDir=EmptyDirVolumeSource(medium="Memory"))
        pod_spec_volumes.append(shm_vol)

        shm_vol_mount = VolumeMount(name=shared_memory_vol, mountPath=SHARED_MEMORY_VOLUME_MOUNT)
        container_volume_mounts.append(shm_vol_mount)

    def dump_yaml_string(self):
        return self.root.to_yaml()

    # TODO: Move this method into the Kubernetes object
    def add_benchmark_cmd_to_container(self):
        """
        Extracts the command and args for the benchmark container, formats and inserts them.
        The command is split into args and passed to the container as a list.
        If a benchmark command was specified, command and args are inserted in the container's command field.
        If only args are provided, they are inserted in the container's args field.
        """
        benchmark_container = self.root.find_container(BENCHMARK_CONTAINER)

        def split_args(command: str) -> List[str]:
            if not command:
                return []
            return shlex.split(command)

        if self.descriptor.benchmark_code:
            cmd = split_args(self.descriptor.benchmark_code)
            args = split_args(self.descriptor.ml_args)
            benchmark_container.command = cmd + args
            benchmark_container.pop("args", None)

        elif self.descriptor.ml_args:
            benchmark_container.args = split_args(self.descriptor.ml_args)
            benchmark_container.pop("command", None)

        else:
            benchmark_container.pop("command", None)
            benchmark_container.pop("args", None)

    # TODO: Move this method into the Kubernetes object
    def add_benchmark_cmd_to_config_map(self):
        """
        Adds the benchmark code and args to the entrypoint configmap.
        """
        if self.descriptor.benchmark_code:
            benchmark_cmd = self.descriptor.benchmark_code + self.descriptor.ml_args
            # Using yaml.PreservedScalarString so multiline strings are printed properly
            # HACK: Depending on yaml here makes this module depend on knowledge of how our Kubernetes classes are
            # implemented
            benchmark_cmd = yaml.scalarstring.PreservedScalarString(benchmark_cmd)

            entrypoint_config_map = self.root.find_config_map(f"entrypoint-{self.job_id}")
            entrypoint_config_map.data["entrypoint.sh"] = benchmark_cmd

        # If no benchmark_code is specified, we don't need to use the configmap as entrypoint
        else:
            self.add_benchmark_cmd_to_container()

    def _get_data_mounts(self, data_sources: List[BaiDataSource]) -> Dict[str, PullerDataSource]:
        """
        Processes the input data sources to get a dict with the required data volumes
        :param data_sources:
        :return:
        """
        # Data destination paths and the corresponding mounted vols

        data_vols = {}

        for idx, data_source in enumerate(data_sources):
            name = "p" + str(idx)
            puller_path = f"/data/{name}"
            data_vols[data_source.path] = PullerDataSource(name, puller_path)

        return data_vols

    def _get_container_volume_mounts(self, data_volumes: Dict[str, PullerDataSource]) -> List[VolumeMount]:
        vol_mounts = []

        for dest_path, vol in data_volumes.items():
            vol_mounts.append(VolumeMount(name=DATASETS_VOLUME_NAME, mountPath=dest_path, subPath=vol.name))
        return vol_mounts

    def _update_data_puller(self, data_volumes: Dict[str, PullerDataSource], data_sources: List[BaiDataSource]):
        """
        Completes the data puller by adding the required arguments and volume mounts.
        If no data sources are found, the data puller is deleted.
        """
        if not data_sources:
            self.root.remove_container(DATA_PULLER_CONTAINER)
            self.root.remove_volume(DATASETS_VOLUME_NAME)
            return

        data_puller = self.root.find_container(DATA_PULLER_CONTAINER)

        s3_objects = []
        for s in data_sources:
            s3_objects.append(
                "{object},{chmod},{path_name}".format(
                    object=s.object, chmod=self.config.puller_mount_chmod, path_name=data_volumes[s.path].name
                )
            )

        puller_args = [data_sources[0].bucket, ":".join(s3_objects)]
        data_puller.args = puller_args

    def add_env_vars(self):
        self.root.add_env_vars(BENCHMARK_CONTAINER, self.descriptor.env_vars)
        self.root.add_env_vars(BENCHMARK_CONTAINER, self.internal_env_vars)

    def add_scripts(self, scripts: List[BaiScriptSource]):
        if not scripts:
            self.root.remove_container(SCRIPTS_PULLER_CONTAINER)
            self.root.remove_volume(SCRIPTS_VOLUME_NAME)
            return
        script_puller = self.root.find_container(SCRIPTS_PULLER_CONTAINER)
        s3_objects = []

        for inx, s in enumerate(scripts):
            s3_objects.append(
                "{object},{chmod},{path_name},{unpack}".format(
                    object=s.object,
                    chmod=SCRIPT_PULLER_CHMOD,
                    path_name=f"{SCRIPTS_MOUNT_PATH}/s{inx}",
                    unpack=SCRIPT_UNPACK_MODIFICATOR,
                )
            )

        puller_args = [scripts[0].bucket, ":".join(s3_objects)]
        script_puller.args = puller_args

        self.internal_env_vars["BAI_SCRIPTS_PATH"] = SCRIPTS_MOUNT_PATH


def create_bai_data_sources(fetched_data_sources: List[DataSet], descriptor: Descriptor) -> List[BaiDataSource]:
    def find_destination_path(fetched_source: DataSet) -> str:
        return descriptor.find_data_source(fetched_source.src)["path"]

    return [BaiDataSource(fetched, find_destination_path(fetched)) for fetched in fetched_data_sources]



def create_scripts(scripts: List[FileSystemObject]) -> List[BaiScriptSource]:
    return list(map(BaiScriptSource, scripts)) if scripts else []

def read_template(template_name: str) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "templates")

    with open(os.path.join(templates_dir, template_name), "r") as f:
        contents = f.read()
    return contents

def create_bai_k8s_builder(
    descriptor: Descriptor,
    bai_config: BaiConfig,
    fetched_data_sources: List[DataSet],
    scripts: List[FileSystemObject],
    job_id: str,
    *,
    event: BenchmarkEvent,
    environment_info: EnvironmentInfo,
    extra_bai_config_args: Dict = None,
) -> BaiKubernetesObjectBuilder:
    """
    Builds a BaiKubernetesObjectBuilder object
    :param event: The event that triggered this execution
    :param descriptor: The descriptor.
    :param bai_config: Configuration values.
    :param fetched_data_sources: list of fetched data sources, as generated by the fetcher.
    :param job_id: str
    :param environment_info: Information on the environment that BAI is running on.
    :param extra_bai_config_args: An optional Dict which will be forwarded to the `BaiConfig` object created.
    :return:
    """
    template_files = {
        DistributedStrategy.SINGLE_NODE: "job_single_node.yaml",
        DistributedStrategy.HOROVOD: "mpi_job_horovod.yaml",
    }

    if extra_bai_config_args is None:
        extra_bai_config_args = {}

    contents = read_template(template_files[descriptor.strategy])
    config_template = ConfigTemplate(contents)
    bai_data_sources = create_bai_data_sources(fetched_data_sources, descriptor)
    bai_scripts = create_scripts(scripts)

    bai_k8s_builder = BaiKubernetesObjectBuilder(
        descriptor,
        bai_config,
        bai_data_sources,
        bai_scripts,
        config_template,
        job_id,
        event=event,
        environment_info=environment_info,
        **extra_bai_config_args,
    )

    if descriptor.strategy == DistributedStrategy.SINGLE_NODE:
        bai_k8s_builder.add_benchmark_cmd_to_container()
    elif descriptor.strategy == DistributedStrategy.HOROVOD:
        bai_k8s_builder.add_benchmark_cmd_to_config_map()
    else:
        raise ValueError("Unsupported configuration in descriptor file")

    return bai_k8s_builder


def create_job_yaml_spec(
    descriptor_contents: Dict,
    executor_config: ExecutorConfig,
    fetched_data_sources: List[DataSet],
    scripts: List[FileSystemObject],
    job_id: str,
    *,
    event: BenchmarkEvent,
    extra_bai_config_args=None,
) -> str:
    """
    Creates the YAML spec file corresponding to a descriptor passed as parameter
    :param event: event that triggered this execution
    :param descriptor_contents: dict containing the parsed descriptor
    :param executor_config: configuration for the transpiler
    :param fetched_data_sources: list of fetched data sources, as generated by the fetcher
    :param scripts: list of supplied scripts
    :param job_id: str
    :param extra_bai_config_args: An optional Dict which will be forwarded to the `BaiConfig` object created
    :return: Tuple with (yaml string for the given descriptor, job_id)
    """
    descriptor = Descriptor(descriptor_contents, executor_config.descriptor_config)
    bai_k8s_builder = create_bai_k8s_builder(
        descriptor,
        executor_config.bai_config,
        fetched_data_sources,
        scripts,
        job_id,
        event=event,
        environment_info=executor_config.environment_info,
        extra_bai_config_args=extra_bai_config_args,
    )
    return bai_k8s_builder.dump_yaml_string()

