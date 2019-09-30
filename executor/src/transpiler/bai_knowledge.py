import abc
import base64
import json
import logging
import os
import random
import shlex
from dataclasses import dataclass
from typing import List, Dict

from bai_kafka_utils.events import DownloadableContent, BenchmarkEvent
from bai_kafka_utils.events import FileSystemObject
from bai_kafka_utils.executors.descriptor import DescriptorError, Descriptor, DistributedStrategy
from ruamel import yaml

from executor import SERVICE_NAME
from executor.config import ExecutorConfig
from transpiler.config import BaiConfig, BaiDataSource, EnvironmentInfo, BaiScriptSource
from transpiler.kubernetes_spec_logic import (
    ConfigTemplate,
    VolumeMount,
    Volume,
    EmptyDirVolumeSource,
    KubernetesRootObjectHelper,
)

SCRIPT_UNPACK_MODIFICATOR = "unpack_in_place"

SCRIPT_PULLER_CHMOD = 777

BENCHMARK_CONTAINER = "benchmark"
DATA_PULLER_CONTAINER = "data-puller"
DATASETS_VOLUME_NAME = "datasets-volume"
SCRIPTS_VOLUME_NAME = "scripts-volume"
SCRIPTS_PULLER_CONTAINER = "script-puller"
INFERENCE_SERVER_LOCK_CONTAINER = "inference-server-lock"
INFERENCE_SERVER_CONTAINER = "inference-server"

# To make things easier it's the same path in puller and benchmark
SCRIPTS_MOUNT_PATH = "/bai/scripts"

SHARED_MEMORY_VOLUME = "dshm"
SHARED_MEMORY_VOLUME_MOUNT = "/dev/shm"


@dataclass
class PullerDataSource:
    name: str
    puller_path: str


logger = logging.getLogger(__name__)


class BaiKubernetesObjectBuilder(metaclass=abc.ABCMeta):
    def __init__(
        self, job_id: str, descriptor: Descriptor, config: BaiConfig, template_name: str, event: BenchmarkEvent
    ):
        self.job_id = job_id.lower()
        self.inference_server_job_id = f"is-{self.job_id}"
        self.descriptor = descriptor
        self.config_template = ConfigTemplate(self.read_template(template_name))
        self.config = config
        self.event = event

        self.root: KubernetesRootObjectHelper = None

        self.config_template.feed({"descriptor": descriptor})
        self.config_template.feed({"config": config})
        self.config_template.feed({"event": event})
        self.config_template.feed({"service_name": SERVICE_NAME})
        self.config_template.feed({"job_id": self.job_id})
        self.config_template.feed({"inference_server_job_id": self.inference_server_job_id})
        self.config_template.feed({"metrics": self.get_metrics_from_descriptor(descriptor)})

    @staticmethod
    def get_metrics_from_descriptor(descriptor: Descriptor):
        metrics = []
        for metric in descriptor.metrics:
            metric["pattern"] = base64.b64encode(metric["pattern"].encode("utf-8")).decode("utf-8")
            metrics.append(metric)
        return json.dumps(metrics)

    @staticmethod
    def read_template(template_name: str) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(current_dir, "templates")

        with open(os.path.join(templates_dir, template_name), "r") as f:
            contents = f.read()
        return contents

    @abc.abstractmethod
    def _feed_additional_template_values(self):
        pass

    @abc.abstractmethod
    def _update_root_k8s_object(self):
        pass

    def build(self):
        # if the root object has already been built don't build it again
        if self.root:
            return

        self._feed_additional_template_values()
        self.root = self.config_template.build()

        for label, value in self.descriptor.custom_labels.items():
            self.root.add_label(label, value)

        self._update_root_k8s_object()
        return self

    def dump_yaml_string(self):
        self.build()
        return self.root.to_yaml()


class ScheduledBenchmarkKubernetedObjectBuilder(BaiKubernetesObjectBuilder):
    def __init__(self, descriptor: Descriptor, config: BaiConfig, job_id: str, event: BenchmarkEvent):
        super().__init__(job_id, descriptor, config, "cron_job.yaml", event)

    def _feed_additional_template_values(self):
        self.config_template.feed({"event_json_str": json.dumps(self.event.to_json())})

    def _update_root_k8s_object(self):
        pass


class SingleRunBenchmarkKubernetesObjectBuilder(BaiKubernetesObjectBuilder):
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
        job_id: str,
        *,
        template_name: str,
        event: BenchmarkEvent,
        environment_info: EnvironmentInfo,
        random_object: random.Random = None,
    ):
        """
        Reads the values from the descriptor file into a settings dictionary
        :param descriptor: Descriptor object with the information from the TOML
        :param random_object: An instance of random.Random [optional].
                              This field exists mostly to facilitate testing so that predictable random data is
                              generated.
        """
        super().__init__(job_id, descriptor, config, template_name=template_name, event=event)

        self.data_sources = data_sources
        self.scripts = scripts
        self.environment_info = environment_info
        self.random_object = random_object
        self.internal_env_vars = {}

    def _feed_additional_template_values(self):
        # Using a random AZ is good enough for now
        availability_zone = self.choose_availability_zone(self.descriptor, self.environment_info, self.random_object)
        self.config_template.feed({"availability_zone": availability_zone})

    def _update_root_k8s_object(self):
        self.add_data_volume_mounts(self.data_sources)
        self.add_scripts(self.scripts)
        self.add_shared_memory()
        self.add_env_vars()
        self.add_benchmark_cmd()

        if self.event.parent_action_id:
            self.root.add_label("parent-action-id", self.event.parent_action_id)

        if self.config.suppress_job_affinity:
            self.root.remove_affinity()

        if self.descriptor.is_client_server:
            # add server environment variables
            self.add_server_env_vars()

        # remove server lock init container from non-client_server strategy
        # single node benchmarks
        elif self.descriptor.strategy == DistributedStrategy.SINGLE_NODE:
            self.root.remove_container(INFERENCE_SERVER_LOCK_CONTAINER)

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

    def add_server_env_vars(self):
        if not self.descriptor.is_client_server:
            return

        # TODO: Maybe the k8s namespace should be a parameter to the configuration
        namespace = "default"

        env_vars = {"INFERENCE_SERVER_HOST": f"{self.inference_server_job_id}.{namespace}"}
        ports = self.descriptor.server.env.ports
        env_vars["INFERENCE_SERVER_PORT"] = ports[0]
        for index, port in enumerate(ports[1:]):
            env_vars[f"INFERENCE_SERVER_PORT_{index + 1}"] = port

        self.root.add_env_vars(BENCHMARK_CONTAINER, env_vars)

    def add_benchmark_cmd(self):
        if self.descriptor.strategy in [DistributedStrategy.SINGLE_NODE, DistributedStrategy.CLIENT_SERVER]:
            self.add_benchmark_cmd_to_container()
        elif self.descriptor.strategy == DistributedStrategy.HOROVOD:
            self.add_benchmark_cmd_to_config_map()
        else:
            raise ValueError("Unsupported configuration in descriptor file")

    def add_data_volume_mounts(self, data_sources):
        benchmark_container = self.root.find_container(BENCHMARK_CONTAINER)
        data_mounts = self._get_data_mounts(data_sources)
        self._update_data_puller(data_mounts, data_sources)
        benchmark_container.volumeMounts.extend(self._get_container_volume_mounts(data_mounts))

    def add_shared_memory(self):
        if self.descriptor.extended_shm:
            self._add_extended_shm()

    def _add_extended_shm(self, container=BENCHMARK_CONTAINER):
        pod_spec_volumes = self.root.get_pod_spec().volumes
        container_volume_mounts = self.root.find_container(container).volumeMounts

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


class InferenceServerJobKubernetedObjectBuilder(SingleRunBenchmarkKubernetesObjectBuilder):
    def __init__(
        self,
        descriptor: Descriptor,
        config: BaiConfig,
        job_id: str,
        event: BenchmarkEvent,
        environment_info: EnvironmentInfo,
        random_object: random.Random = None,
    ):
        super().__init__(
            descriptor,
            config,
            [],
            [],
            job_id,
            template_name="inference_server_job.yaml",
            event=event,
            environment_info=environment_info,
            random_object=random_object,
        )

    def _feed_additional_template_values(self):
        super()._feed_additional_template_values()

    def _update_root_k8s_object(self):
        self.add_shared_memory()
        self.add_server_command_to_container()
        self.root.add_env_vars(INFERENCE_SERVER_CONTAINER, self.descriptor.server.env.vars)
        self.root.add_tcp_ports_to_service(self.inference_server_job_id, self.descriptor.server.env.ports)
        self.root.add_container_ports_to_container(INFERENCE_SERVER_CONTAINER, self.descriptor.server.env.ports)
        if self.event.parent_action_id:
            self.root.add_label("parent-action-id", self.event.parent_action_id)

    def add_shared_memory(self):
        if self.descriptor.server.env.extended_shm:
            self._add_extended_shm(container=INFERENCE_SERVER_CONTAINER)

    # TODO: Move this method into the Kubernetes object
    def add_server_command_to_container(self):
        """
        Extracts the command and args for the server container, formats and inserts them.
        The command is split into args and passed to the container as a list.
        If a server command was specified, command and args are inserted in the container's command field.
        If only args are provided, they are inserted in the container's args field.
        """
        server_container = self.root.find_container(INFERENCE_SERVER_CONTAINER)

        def split_args(command: str) -> List[str]:
            if not command:
                return []
            return shlex.split(command)

        cmd = split_args(self.descriptor.server.env.start_command)
        args = split_args(self.descriptor.server.env.start_command_args)
        server_container.command = cmd + args
        server_container.pop("args", None)


def create_bai_data_sources(
    fetched_data_sources: List[DownloadableContent], descriptor: Descriptor
) -> List[BaiDataSource]:
    def find_destination_path(fetched_source: DownloadableContent) -> str:
        return descriptor.find_data_source(fetched_source.src)["path"]

    return [BaiDataSource(fetched, find_destination_path(fetched)) for fetched in fetched_data_sources]


def create_scripts(scripts: List[FileSystemObject]) -> List[BaiScriptSource]:
    return list(map(BaiScriptSource, scripts)) if scripts else []


def create_single_run_benchmark_bai_k8s_builder(
    descriptor: Descriptor,
    bai_config: BaiConfig,
    fetched_data_sources: List[DownloadableContent],
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
    if extra_bai_config_args is None:
        extra_bai_config_args = {}

    template_files = {
        DistributedStrategy.SINGLE_NODE: "job_single_node.yaml",
        DistributedStrategy.HOROVOD: "mpi_job_horovod.yaml",
        # Benchmark job component of client-server strategy
        DistributedStrategy.CLIENT_SERVER: "job_single_node.yaml",
    }

    template_name = template_files.get(descriptor.strategy)
    if not template_name:
        raise ValueError(f"Unsupported distributed strategy in descriptor file: '{descriptor.strategy}'")

    bai_data_sources = create_bai_data_sources(fetched_data_sources, descriptor)
    bai_scripts = create_scripts(scripts)

    bai_k8s_builder = SingleRunBenchmarkKubernetesObjectBuilder(
        descriptor,
        bai_config,
        bai_data_sources,
        bai_scripts,
        job_id,
        template_name=template_name,
        event=event,
        environment_info=environment_info,
        **extra_bai_config_args,
    )

    return bai_k8s_builder.build()


def create_inference_server_bai_k8s_builder(
    descriptor: Descriptor,
    bai_config: BaiConfig,
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
    :param job_id: str
    :param environment_info: Information on the environment that BAI is running on
    :param extra_bai_config_args: An optional Dict which will be forwarded to the `BaiConfig` object created
    :return:
    """

    if extra_bai_config_args is None:
        extra_bai_config_args = {}

    bai_k8s_builder = InferenceServerJobKubernetedObjectBuilder(
        descriptor, bai_config, job_id, event=event, environment_info=environment_info, **extra_bai_config_args
    )
    return bai_k8s_builder.build()


def create_scheduled_benchmark_bai_k8s_builder(
    descriptor: Descriptor, bai_config: BaiConfig, job_id: str, event: BenchmarkEvent
) -> ScheduledBenchmarkKubernetedObjectBuilder:
    """
    Builds a BaiKubernetesObjectBuilder object
    :param event: The event that triggered this execution
    :param descriptor: The descriptor.
    :param bai_config: Configuration values.
    :param job_id: str
    :return:
    """
    bai_k8s_builder = ScheduledBenchmarkKubernetedObjectBuilder(descriptor, bai_config, job_id, event)
    return bai_k8s_builder.build()


def create_job_yaml_spec(
    descriptor_contents: Dict,
    executor_config: ExecutorConfig,
    fetched_data_sources: List[DownloadableContent],
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

    bai_k8s_benchmark_job_builder = create_single_run_benchmark_bai_k8s_builder(
        descriptor,
        executor_config.bai_config,
        fetched_data_sources,
        scripts,
        job_id,
        event=event,
        environment_info=executor_config.environment_info,
        extra_bai_config_args=extra_bai_config_args,
    )

    if descriptor.strategy != DistributedStrategy.CLIENT_SERVER:
        return bai_k8s_benchmark_job_builder.dump_yaml_string()

    bai_k8s_inference_server_job_builder = create_inference_server_bai_k8s_builder(
        descriptor,
        executor_config.bai_config,
        job_id,
        event=event,
        environment_info=executor_config.environment_info,
        extra_bai_config_args=extra_bai_config_args,
    )

    return (
        f"{bai_k8s_benchmark_job_builder.dump_yaml_string()}"
        f"---\n"
        f"{bai_k8s_inference_server_job_builder.dump_yaml_string()}"
    )


def create_scheduled_job_yaml_spec(
    descriptor_contents: Dict, executor_config: ExecutorConfig, job_id: str, event: BenchmarkEvent
) -> str:
    """
    Creates the YAML spec file corresponding to a descriptor passed as parameter
    :param event: event that triggered this execution
    :param descriptor_contents: dict containing the parsed descriptor
    :param executor_config: configuration for the transpiler
    :param job_id: str
    :return: Tuple with (yaml string for the given descriptor, job_id)
    """
    descriptor = Descriptor(descriptor_contents, executor_config.descriptor_config)
    bai_k8s_builder = create_scheduled_benchmark_bai_k8s_builder(
        descriptor, executor_config.bai_config, job_id, event=event
    )
    return bai_k8s_builder.dump_yaml_string()
