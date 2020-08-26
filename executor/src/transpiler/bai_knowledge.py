import abc
import base64
import json
import logging
import os
import random
import shlex
from dataclasses import dataclass, asdict
from typing import List, Dict
from urllib.parse import urlparse

from bai_kafka_utils.events import DownloadableContent, BenchmarkEvent
from bai_kafka_utils.events import FileSystemObject
from bai_kafka_utils.executors.descriptor import (
    DescriptorError,
    BenchmarkDescriptor,
    DistributedStrategy,
    MPI_JOB_LAUNCHER,
    MPI_JOB_WORKER,
)
from bai_kafka_utils.utils import METRICS_PUSHER_CUSTOM_LABEL_PREFIX
from ruamel import yaml

from executor import SERVICE_NAME
from executor.config import ExecutorConfig
from transpiler.config import BaiConfig, EnvironmentInfo, BaiScriptSource
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
METRICS_PUSHER_CONTAINER = "metrics-pusher"
METRICS_EXTRACTOR_CONTAINER = "metrics-extractor"
DATASETS_VOLUME_NAME = "datasets-volume"
SCRIPTS_VOLUME_NAME = "scripts-volume"
SCRIPTS_PULLER_CONTAINER = "script-puller"
INFERENCE_SERVER_LOCK_CONTAINER = "inference-server-lock"
INFERENCE_SERVER_CONTAINER = "inference-server"
# To make things easier it's the same path in puller and benchmark
SCRIPTS_MOUNT_PATH = "/bai/scripts"

SHARED_MEMORY_VOLUME = "dshm"
SHARED_MEMORY_VOLUME_MOUNT = "/dev/shm"

BENCHMARK_SERVICE_ACCOUNT = "benchmark"
INFERENCE_SERVER_SERVICE_ACCOUNT = "inference-benchmark"


@dataclass
class PullerDataSource:
    name: str
    puller_path: str


logger = logging.getLogger(__name__)


class BaiKubernetesObjectBuilder(metaclass=abc.ABCMeta):
    def __init__(
        self, job_id: str, descriptor: BenchmarkDescriptor, config: BaiConfig, template_name: str, event: BenchmarkEvent
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

    @staticmethod
    def get_metrics_from_descriptor(descriptor: BenchmarkDescriptor):
        metrics = []
        if descriptor.output:
            for metric in descriptor.output.metrics:
                metric.pattern = base64.b64encode(metric.pattern.encode("utf-8")).decode("utf-8")
                metrics.append(asdict(metric))
        return json.dumps(metrics)

    @staticmethod
    def get_server_metrics_from_descriptor(descriptor: BenchmarkDescriptor):
        metrics = []
        if descriptor.is_inference_strategy() and descriptor.server.output:
            for metric in descriptor.server.output.metrics:
                metric.pattern = base64.b64encode(metric.pattern.encode("utf-8")).decode("utf-8")
                metrics.append(asdict(metric))
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

        for label, value in self.descriptor.info.labels.items():
            self.root.add_label(label, value)

        self._update_root_k8s_object()
        return self

    def dump_yaml_string(self):
        self.build()
        return self.root.to_yaml()


class ScheduledBenchmarkKubernetedObjectBuilder(BaiKubernetesObjectBuilder):
    def __init__(self, descriptor: BenchmarkDescriptor, config: BaiConfig, job_id: str, event: BenchmarkEvent):
        super().__init__(job_id, descriptor, config, "cron_job.yaml", event)

    def _feed_additional_template_values(self):
        self.config_template.feed({"event_json_str": json.dumps(self.event.to_json())})

    def _update_root_k8s_object(self):
        pass


class BenchmarkKubernetesObjectBuilder(BaiKubernetesObjectBuilder):
    """
    Adds the logic required from BAI into the Kubernetes root object that represents
    launching a benchmark.
    """

    def __init__(
        self,
        descriptor: BenchmarkDescriptor,
        config: BaiConfig,
        data_sources: List[DownloadableContent],
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
        self.config_template.feed({"metrics": self.get_metrics_from_descriptor(self.descriptor)})

    def _update_root_k8s_object(self):
        pass

    @staticmethod
    def choose_availability_zone(
        descriptor: BenchmarkDescriptor, environment_info: EnvironmentInfo, random_object: random.Random = None
    ):
        if descriptor.hardware.availability_zone:
            if descriptor.hardware.availability_zone in environment_info.availability_zones.values():
                return descriptor.hardware.availability_zone
            raise DescriptorError(f"Invalid zone name {descriptor.hardware.availability_zone}")
        # Try to find the zone id
        if descriptor.hardware.aws_zone_id:
            if descriptor.hardware.aws_zone_id in environment_info.availability_zones:
                return environment_info.availability_zones[descriptor.hardware.aws_zone_id]
            raise DescriptorError(f"Invalid zone id {descriptor.hardware.aws_zone_id}")

        if random_object is None:
            random_object = random.Random()

        return random_object.choice(list(environment_info.availability_zones.values()))

    def add_metrics_pusher_env_var(self, key: str, value: str, prefix: str, **kwargs):
        env_var_name = prefix.upper() + key.upper()
        try:
            metrics_pusher_container = self.root.find_container(METRICS_PUSHER_CONTAINER, **kwargs)
        except ValueError:
            logger.debug(f"Could not add env var {env_var_name} to metrics pusher sidecar.")
            return
        metrics_pusher_env = metrics_pusher_container.get("env", [])
        metrics_pusher_env.append({"name": env_var_name, "value": value})

    def add_server_env_vars(self):
        if not self.descriptor.is_inference_strategy:
            return

        # TODO: Maybe the k8s namespace should be a parameter to the configuration
        namespace = "default"

        env_vars = {"INFERENCE_SERVER_HOST": f"{self.inference_server_job_id}.{namespace}"}
        ports = self.descriptor.server.env.ports
        env_vars["INFERENCE_SERVER_PORT"] = ports[0]
        for index, port in enumerate(ports[1:]):
            env_vars[f"INFERENCE_SERVER_PORT_{index + 1}"] = port

        self.root.add_env_vars(BENCHMARK_CONTAINER, env_vars)

    def add_benchmark_cmd(self, **kwargs):
        if self.descriptor.hardware.strategy in [DistributedStrategy.SINGLE_NODE, DistributedStrategy.INFERENCE]:
            self.add_benchmark_cmd_to_container()
        elif self.descriptor.hardware.strategy == DistributedStrategy.HOROVOD:
            self.add_benchmark_cmd_to_config_map(**kwargs)
        else:
            raise ValueError("Unsupported configuration in descriptor file")

    def add_data_volume_mounts(self, data_sources, container: str, **kwargs):
        benchmark_container = self.root.find_container(container, **kwargs)
        data_mounts = self._get_data_mounts(data_sources)
        self._update_data_puller(data_mounts, data_sources, **kwargs)
        benchmark_container.volumeMounts.extend(self._get_container_volume_mounts(data_mounts))

    def remove_metrics_sidecars(self, **kwargs):
        self.root.remove_container(METRICS_EXTRACTOR_CONTAINER, **kwargs)
        self.root.remove_container(METRICS_PUSHER_CONTAINER, **kwargs)

    def add_shared_memory(self, **kwargs):
        if self.descriptor.env.extended_shm:
            self._add_extended_shm(**kwargs)

    def _add_extended_shm(self, container=BENCHMARK_CONTAINER, **kwargs):
        pod_spec_volumes = self.root.get_pod_spec(**kwargs).volumes
        container_volume_mounts = self.root.find_container(container, **kwargs).volumeMounts

        shared_memory_vol = SHARED_MEMORY_VOLUME

        shm_vol = Volume(name=shared_memory_vol, emptyDir=EmptyDirVolumeSource(medium="Memory"))
        pod_spec_volumes.append(shm_vol)

        shm_vol_mount = VolumeMount(name=shared_memory_vol, mountPath=SHARED_MEMORY_VOLUME_MOUNT)
        container_volume_mounts.append(shm_vol_mount)

    def dump_yaml_string(self):
        return self.root.to_yaml()

    # TODO: Move this method into the Kubernetes object
    def add_benchmark_cmd_to_container(self, **kwargs):
        """
        Extracts the command and args for the benchmark container, formats and inserts them.
        The command is split into args and passed to the container as a list.
        If a benchmark command was specified, command and args are inserted in the container's command field.
        If only args are provided, they are inserted in the container's args field.
        """
        benchmark_container = self.root.find_container(BENCHMARK_CONTAINER, **kwargs)

        def split_args(command: str) -> List[str]:
            if not command:
                return []
            return shlex.split(command)

        if self.descriptor.ml and self.descriptor.ml.benchmark_code:
            cmd = split_args(self.descriptor.ml.benchmark_code)
            args = split_args(self.descriptor.ml.args)
            benchmark_container.command = cmd + args
            benchmark_container.pop("args", None)

        elif self.descriptor.ml and self.descriptor.ml.args:
            benchmark_container.args = split_args(self.descriptor.ml.args)
            benchmark_container.pop("command", None)

        else:
            benchmark_container.pop("command", None)
            benchmark_container.pop("args", None)

    # TODO: Move this method into the Kubernetes object
    def add_benchmark_cmd_to_config_map(self, **kwargs):
        """
        Adds the benchmark code and args to the entrypoint configmap.
        """
        if self.descriptor.ml and self.descriptor.ml.benchmark_code:
            benchmark_cmd = self.descriptor.ml.benchmark_code + (self.descriptor.ml.args or "")
            # Using yaml.PreservedScalarString so multiline strings are printed properly
            # HACK: Depending on yaml here makes this module depend on knowledge of how our Kubernetes classes are
            # implemented
            # strip whitespaces from lines as they can cause the script to fail
            benchmark_cmd = "\n".join([line.strip() for line in benchmark_cmd.split("\n")])
            benchmark_cmd = yaml.scalarstring.PreservedScalarString(benchmark_cmd)

            entrypoint_config_map = self.root.find_config_map(f"entrypoint-{self.job_id}")
            entrypoint_config_map.data["entrypoint.sh"] = benchmark_cmd

        # If no benchmark_code is specified, we don't need to use the configmap as entrypoint
        else:
            self.add_benchmark_cmd_to_container(**kwargs)

    def _get_data_mounts(self, data_sources: List[DownloadableContent]) -> Dict[str, PullerDataSource]:
        """
        Processes the input data sources to get a dict with the required data volumes
        :param data_sources:
        :return:
        """
        # Data destination paths and the corresponding mounted vols

        data_vols = {}

        for idx, data_source in enumerate(data_sources):
            if data_source.path in data_vols:
                continue
            name = "p" + str(idx)
            puller_path = f"/data/{name}"
            data_vols[data_source.path] = PullerDataSource(name, puller_path)

        return data_vols

    @staticmethod
    def _get_container_volume_mounts(data_volumes: Dict[str, PullerDataSource]) -> List[VolumeMount]:
        vol_mounts = []

        for dest_path, vol in data_volumes.items():
            vol_mounts.append(VolumeMount(name=DATASETS_VOLUME_NAME, mountPath=dest_path, subPath=vol.name))
        return vol_mounts

    @staticmethod
    def _get_s3_bucket_and_object_from_uri(downloadable_content: DownloadableContent):
        parsed_uri = urlparse(downloadable_content.dst)
        scheme = parsed_uri.scheme
        s3_bucket = parsed_uri.netloc
        s3_object = parsed_uri.path[1:]

        if scheme.lower() != "s3":
            raise DescriptorError(
                f"Unexpected scheme in data source src: {scheme}." f" Fetched content is {downloadable_content}"
            )

        return s3_bucket, s3_object

    def _update_data_puller(
        self, data_volumes: Dict[str, PullerDataSource], data_sources: List[DownloadableContent], **kwargs
    ):
        """
        Completes the data puller by adding the required arguments and volume mounts.
        If no data sources are found, the data puller is deleted.
        """
        if not data_sources:
            self.root.remove_container(DATA_PULLER_CONTAINER, **kwargs)
            self.root.remove_volume(DATASETS_VOLUME_NAME, **kwargs)
            return

        data_puller = self.root.find_container(DATA_PULLER_CONTAINER, **kwargs)

        s3_bucket, _ = self._get_s3_bucket_and_object_from_uri(data_sources[0])

        s3_objects = []
        for s in data_sources:
            _, s3_object = self._get_s3_bucket_and_object_from_uri(s)
            s3_objects.append(
                "{object},{chmod},{path_name}".format(
                    object=s3_object, chmod=self.config.puller_mount_chmod, path_name=data_volumes[s.path].name
                )
            )

        puller_args = [s3_bucket, ":".join(s3_objects)]
        data_puller.args = puller_args

    def add_env_vars(self, **kwargs):
        self.root.add_env_vars(BENCHMARK_CONTAINER, self.descriptor.env.vars, **kwargs)
        self.root.add_env_vars(BENCHMARK_CONTAINER, self.internal_env_vars, **kwargs)

    def add_scripts(self, scripts: List[BaiScriptSource], **kwargs):
        if not scripts:
            self.root.remove_container(SCRIPTS_PULLER_CONTAINER, **kwargs)
            self.root.remove_volume(SCRIPTS_VOLUME_NAME, **kwargs)
            return
        script_puller = self.root.find_container(SCRIPTS_PULLER_CONTAINER, **kwargs)
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


class SingleRunBenchmarkKubernetesObjectBuilder(BenchmarkKubernetesObjectBuilder):
    """
    Adds the logic into the Kubernetes root object that represents launching a benchmark for single node job
    """

    def __init__(
        self,
        descriptor: BenchmarkDescriptor,
        config: BaiConfig,
        data_sources: List[DownloadableContent],
        scripts: List[BaiScriptSource],
        job_id: str,
        *,
        template_name: str,
        event: BenchmarkEvent,
        environment_info: EnvironmentInfo,
        random_object: random.Random = None,
    ):
        super().__init__(
            descriptor,
            config,
            data_sources,
            scripts,
            job_id,
            template_name=template_name,
            event=event,
            environment_info=environment_info,
            random_object=random_object,
        )

    def _feed_additional_template_values(self):
        super()._feed_additional_template_values()

    def _update_root_k8s_object(self):
        self.root.set_service_account(BENCHMARK_SERVICE_ACCOUNT)
        self.add_data_volume_mounts(self.data_sources, BENCHMARK_CONTAINER)
        self.add_scripts(self.scripts)
        self.add_shared_memory()
        self.add_env_vars()
        self.add_benchmark_cmd()

        if not self.descriptor.output:
            self.remove_metrics_sidecars()
        else:
            # Add custom labels metrics pusher
            for label, value in self.descriptor.info.labels.items():
                self.add_metrics_pusher_env_var(label, value, prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX)
            if self.descriptor.custom_params and self.descriptor.custom_params.dashboard:
                self.root.add_label("dashboard-name", self.descriptor.custom_params.dashboard)
                self.add_metrics_pusher_env_var(
                    "dashboard-name", self.descriptor.custom_params.dashboard, prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX
                )
            if self.descriptor.custom_params and self.descriptor.custom_params.region:
                self.root.add_label("region", self.descriptor.custom_params.dashboard)
                self.add_metrics_pusher_env_var(
                    "region", self.descriptor.custom_params.region, prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX
                )

        if self.event.parent_action_id:
            self.root.add_label("parent-action-id", self.event.parent_action_id)
            self.add_metrics_pusher_env_var(
                "parent-action-id", self.event.parent_action_id, prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX
            )

        if self.config.suppress_job_affinity:
            self.root.remove_affinity()

        if self.descriptor.is_inference_strategy():
            # Use inference server service account
            self.root.set_service_account(INFERENCE_SERVER_SERVICE_ACCOUNT)
            # add server environment variables
            self.add_server_env_vars()

        # remove server lock init container from non-inference strategy
        # single node benchmarks
        elif self.descriptor.hardware.strategy == DistributedStrategy.SINGLE_NODE:
            self.root.remove_container(INFERENCE_SERVER_LOCK_CONTAINER)


class HorovodJobKubernetesObjectBuilder(BenchmarkKubernetesObjectBuilder):
    """
    Adds the logic into the Kubernetes root object that represents launching a benchmark for MPIJob
    """

    def __init__(
        self,
        descriptor: BenchmarkDescriptor,
        config: BaiConfig,
        data_sources: List[DownloadableContent],
        scripts: List[BaiScriptSource],
        job_id: str,
        *,
        template_name: str,
        event: BenchmarkEvent,
        environment_info: EnvironmentInfo,
        random_object: random.Random = None,
    ):
        super().__init__(
            descriptor,
            config,
            data_sources,
            scripts,
            job_id,
            template_name=template_name,
            event=event,
            environment_info=environment_info,
            random_object=random_object,
        )

    def _feed_additional_template_values(self):
        super()._feed_additional_template_values()

    def _update_root_k8s_object(self):
        self.add_data_volume_mounts(self.data_sources, BENCHMARK_CONTAINER, mpiReplicaType=MPI_JOB_WORKER)
        self.add_benchmark_cmd(mpiReplicaType=MPI_JOB_LAUNCHER)

        for replica_type in [MPI_JOB_LAUNCHER, MPI_JOB_WORKER]:
            self.root.set_service_account(BENCHMARK_SERVICE_ACCOUNT, mpiReplicaType=replica_type)
            self.add_scripts(self.scripts, mpiReplicaType=replica_type)
            self.add_shared_memory(mpiReplicaType=replica_type)
            self.add_env_vars(mpiReplicaType=replica_type)

            if not self.descriptor.output:
                self.remove_metrics_sidecars(mpiReplicaType=replica_type)
            else:
                # Add custom labels metrics pusher
                for label, value in self.descriptor.info.labels.items():
                    self.add_metrics_pusher_env_var(
                        label, value, prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX, mpiReplicaType=replica_type
                    )
                if self.descriptor.custom_params and self.descriptor.custom_params.dashboard:
                    self.root.add_label("dashboard-name", self.descriptor.custom_params.dashboard)
                    self.add_metrics_pusher_env_var(
                        "dashboard-name",
                        self.descriptor.custom_params.dashboard,
                        prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX,
                        mpiReplicaType=replica_type,
                    )
                if self.descriptor.custom_params and self.descriptor.custom_params.region:
                    self.root.add_label("region", self.descriptor.custom_params.dashboard)
                    self.add_metrics_pusher_env_var(
                        "region",
                        self.descriptor.custom_params.region,
                        prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX,
                        mpiReplicaType=replica_type,
                    )

            if self.event.parent_action_id:
                self.root.add_label("parent-action-id", self.event.parent_action_id)
                self.add_metrics_pusher_env_var(
                    "parent-action-id",
                    self.event.parent_action_id,
                    prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX,
                    mpiReplicaType=replica_type,
                )

            if self.config.suppress_job_affinity:
                self.root.remove_affinity(mpiReplicaType=replica_type)


class InferenceServerJobKubernetedObjectBuilder(BenchmarkKubernetesObjectBuilder):
    def __init__(
        self,
        descriptor: BenchmarkDescriptor,
        config: BaiConfig,
        job_id: str,
        fetched_models: List[DownloadableContent],
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
        self.fetched_models = fetched_models

    def _feed_additional_template_values(self):
        super()._feed_additional_template_values()
        self.config_template.feed({"server_metrics": self.get_server_metrics_from_descriptor(self.descriptor)})

    def _update_root_k8s_object(self):
        self.root.set_service_account(INFERENCE_SERVER_SERVICE_ACCOUNT)
        self.add_shared_memory()
        self.add_server_command_to_container()
        self.add_data_volume_mounts(self.fetched_models, INFERENCE_SERVER_CONTAINER)
        self.root.add_env_vars(INFERENCE_SERVER_CONTAINER, self.descriptor.server.env.vars)
        self.root.add_tcp_ports_to_service(self.inference_server_job_id, self.descriptor.server.env.ports)
        self.root.add_container_ports_to_container(INFERENCE_SERVER_CONTAINER, self.descriptor.server.env.ports)
        if self.descriptor.server.env.readiness_probe:
            self.root.add_readiness_probe(
                container_name=INFERENCE_SERVER_CONTAINER,
                probe=self.descriptor.server.env.readiness_probe,
                default_port=self.descriptor.server.env.ports[0],
            )
        if self.event.parent_action_id:
            self.root.add_label("parent-action-id", self.event.parent_action_id)
        if not self.descriptor.server.output:
            self.remove_metrics_sidecars()
        else:
            # Add custom labels to metrics pusher as env variables
            for label, value in self.descriptor.info.labels.items():
                self.add_metrics_pusher_env_var(label, value, METRICS_PUSHER_CUSTOM_LABEL_PREFIX)
            if self.descriptor.custom_params and self.descriptor.custom_params.dashboard:
                self.root.add_label("dashboard-name", self.descriptor.custom_params.dashboard)
                self.add_metrics_pusher_env_var(
                    "dashboard-name", self.descriptor.custom_params.dashboard, prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX
                )
            if self.descriptor.custom_params and self.descriptor.custom_params.region:
                self.root.add_label("region", self.descriptor.custom_params.dashboard)
                self.add_metrics_pusher_env_var(
                    "region", self.descriptor.custom_params.region, prefix=METRICS_PUSHER_CUSTOM_LABEL_PREFIX
                )
        if self.config.suppress_job_affinity:
            self.root.remove_affinity()

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


def create_scripts(scripts: List[FileSystemObject]) -> List[BaiScriptSource]:
    return list(map(BaiScriptSource, scripts)) if scripts else []


def create_single_run_benchmark_bai_k8s_builder(
    descriptor: BenchmarkDescriptor,
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

    distributed_strategy_metadata = {
        DistributedStrategy.SINGLE_NODE: {
            "template_name": "job_single_node.yaml",
            "strategy_type_class": SingleRunBenchmarkKubernetesObjectBuilder,
        },
        DistributedStrategy.INFERENCE: {
            # Benchmark job component of inference strategy
            "template_name": "job_single_node.yaml",
            "strategy_type_class": SingleRunBenchmarkKubernetesObjectBuilder,
        },
        DistributedStrategy.HOROVOD: {
            "template_name": "mpi_job_horovod.yaml",
            "strategy_type_class": HorovodJobKubernetesObjectBuilder,
        },
    }

    template_name = distributed_strategy_metadata.get(descriptor.hardware.strategy)["template_name"]
    if not template_name:
        raise ValueError(f"Unsupported distributed strategy in descriptor file: '{descriptor.hardware.strategy}'")

    bai_scripts = create_scripts(scripts)

    bai_k8s_builder = distributed_strategy_metadata.get(descriptor.hardware.strategy)["strategy_type_class"](
        descriptor,
        bai_config,
        fetched_data_sources,
        bai_scripts,
        job_id,
        template_name=template_name,
        event=event,
        environment_info=environment_info,
        **extra_bai_config_args,
    )

    return bai_k8s_builder.build()


def create_inference_server_bai_k8s_builder(
    descriptor: BenchmarkDescriptor,
    bai_config: BaiConfig,
    job_id: str,
    fetched_models: List[DownloadableContent],
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
        descriptor,
        bai_config,
        job_id,
        fetched_models,
        event=event,
        environment_info=environment_info,
        **extra_bai_config_args,
    )
    return bai_k8s_builder.build()


def create_scheduled_benchmark_bai_k8s_builder(
    descriptor: BenchmarkDescriptor, bai_config: BaiConfig, job_id: str, event: BenchmarkEvent
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
    descriptor_contents: Dict[str, str],
    executor_config: ExecutorConfig,
    fetched_data_sources: List[DownloadableContent],
    fetched_models: List[DownloadableContent],
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
    :param fetched_models: list of fetched models, as generated by the fetcher
    :param scripts: list of supplied scripts
    :param job_id: str
    :param extra_bai_config_args: An optional Dict which will be forwarded to the `BaiConfig` object created
    :return: Tuple with (yaml string for the given descriptor, job_id)
    """
    descriptor = BenchmarkDescriptor.from_dict(descriptor_contents, executor_config.descriptor_config)

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

    if descriptor.hardware.strategy != DistributedStrategy.INFERENCE:
        return bai_k8s_benchmark_job_builder.dump_yaml_string()

    bai_k8s_inference_server_job_builder = create_inference_server_bai_k8s_builder(
        descriptor,
        executor_config.bai_config,
        job_id,
        fetched_models,
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
    descriptor = BenchmarkDescriptor.from_dict(descriptor_contents, executor_config.descriptor_config)
    bai_k8s_builder = create_scheduled_benchmark_bai_k8s_builder(
        descriptor, executor_config.bai_config, job_id, event=event
    )
    return bai_k8s_builder.dump_yaml_string()
