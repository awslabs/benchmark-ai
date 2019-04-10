import os
import random
import shlex
import uuid
from typing import List, Dict

from ruamel import yaml

from transpiler.descriptor import Descriptor
from transpiler.kubernetes_spec_logic import ConfigTemplate, VolumeMount, HostPath, Volume, EmptyDirVolumeSource


class BaiConfig:
    """
    Adds the logic required from BAI into the Kubernetes root object that represents
    launching a benchmark.
    """
    MOUNT_CHMOD = '777'
    SHARED_MEMORY_VOL = 'dshm'

    # TODO: Figure out how to coordinate fetcher and puller
    S3_REGION = 'eu-west-1'
    PULLER_IMAGE = 'stsukrov/s3dataprovider'

    def __init__(self, descriptor: Descriptor, config_template: ConfigTemplate, *, random_object=None):
        """
        Reads the values from the transpiler file into a settings dictionary
        :param descriptor: Descriptor object with the information from the TOML
        :param config_template: The YAML template
        :param random_object: An instance of random.Random [optional].
                              This field exists mostly to facilitate testing so that predictable random data is
                              generated.
        """
        self.descriptor = descriptor

        if random_object is None:
            random_object = random.Random()

        # random_object.getrandbits(128) is equivalent to os.urandom(16), since 16 * 8 = 128
        self.job_id = uuid.UUID(int=random_object.getrandbits(128), version=4).hex

        config_template.feed(vars(self.descriptor))
        config_template.feed({"job_id": self.job_id})
        self.root = config_template.build()
        self.add_volumes()

    def add_volumes(self):
        data_volumes = self._get_data_volumes(self.descriptor.data_sources)

        benchmark_container = self.root.find_container("benchmark")
        pod_spec = self.root.get_pod_spec()

        self._update_data_puller(data_volumes, self.descriptor.data_sources)

        benchmark_container.volumeMounts.extend(self._get_container_volume_mounts(data_volumes))
        pod_spec.volumes.extend(self._get_pod_spec_volumes(data_volumes))

        if self.descriptor.extended_shm:
            self.add_extended_shm()

    def add_extended_shm(self):
        pod_spec_volumes = self.root.get_pod_spec().volumes
        container_volume_mounts = self.root.find_container("benchmark").volumeMounts

        shm_vol = Volume(name=self.SHARED_MEMORY_VOL,
                         emptyDir=EmptyDirVolumeSource(medium="Memory"))
        pod_spec_volumes.append(shm_vol)

        shm_vol_mount = VolumeMount(name=self.SHARED_MEMORY_VOL,
                                    mountPath='/dev/shm')
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
        benchmark_container = self.root.find_container('benchmark')

        def split_args(command: str) -> List[str]:
            if not command:
                return []
            return shlex.split(command)

        if self.descriptor.benchmark_code:
            cmd = split_args(self.descriptor.benchmark_code)
            args = split_args(self.descriptor.ml_args)
            benchmark_container.command = cmd + args
            benchmark_container.pop('args', None)

        elif self.descriptor.ml_args:
            benchmark_container.args = split_args(self.descriptor.ml_args)
            benchmark_container.pop('command', None)

        else:
            benchmark_container.pop('command', None)
            benchmark_container.pop('args', None)

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

            entrypoint_config_map = self.root.find_config_map(f'entrypoint-{self.job_id}')
            entrypoint_config_map.data.entrypoint = benchmark_cmd

        # If no benchmark_code is specified, we don't need to use the configmap as entrypoint
        else:
            self.add_benchmark_cmd_to_container()

    def _get_data_volumes(self, data_sources: List) -> Dict:
        """
        Processes the input data sources to get a dict with the required data volumes
        :param data_sources:
        :return:
        """
        # Data destination paths and the corresponding mounted vols
        destination_paths = {s['path'] for s in data_sources}
        data_vols = {}

        for idx, dest in enumerate(destination_paths):
            name = 'p' + str(idx)
            puller_path = f'/data/{name}'
            data_vols[dest] = {'name': name,
                               'puller_path': puller_path}

        return data_vols

    def _get_pod_spec_volumes(self, data_volumes) -> List[Volume]:
        volumes = []

        for vol in data_volumes.values():
            volumes.append(Volume(name=vol['name'],
                                  hostPath=HostPath(path=f'/{vol["name"]}',
                                                    type='DirectoryOrCreate')))
        return volumes

    def _get_container_volume_mounts(self, data_volumes) -> List[VolumeMount]:
        vol_mounts = []

        for dest_path, vol in data_volumes.items():
            vol_mounts.append(VolumeMount(name=vol['name'],
                                          mountPath=dest_path))
        return vol_mounts

    def _update_data_puller(self, data_volumes, data_sources):
        """
        Completes the data puller by adding the required arguments and volume mounts.

        If no data sources are found, the data puller is deleted.
        """

        if not data_sources:
            self.root.remove_container("data-puller")
            return

        data_puller = self.root.find_container("data-puller")

        # Placeholder until the data fetcher is ready
        # ------------------------------------------
        s3_objects = []
        for s in data_sources:
            s3_objects.append(s['object'] + ',' +
                              self.MOUNT_CHMOD + ',' +
                              data_volumes[s['path']]['name'])

        puller_args = [self.S3_REGION, data_sources[0]['bucket'], ':'.join(s3_objects)]
        # ------------------------------------------

        vol_mounts = self._get_puller_volume_mounts(data_volumes)
        data_puller.image = self.PULLER_IMAGE
        data_puller.args = puller_args
        if not data_puller.volumeMounts:
            data_puller.volumeMounts = vol_mounts
        else:
            data_puller.volumeMounts.extend(vol_mounts)

    def _get_puller_volume_mounts(self, data_volumes) -> List[VolumeMount]:
        vol_mounts = []

        for vol in data_volumes.values():
            vol_mounts.append(VolumeMount(name=vol['name'],
                                          mountPath=vol['puller_path']))

        return vol_mounts


def create_bai_config(descriptor: Descriptor, extra_bai_config_args=None) -> BaiConfig:
    """
    Builds a BaiConfig object

    :param descriptor: The transpiler.
    :param extra_bai_config_args: An optional Dict which will be forwarded to the `BaiConfig` object created.
    :return:
    """
    template_files = {
        'single_node': "job_single_node.yaml",
        'horovod': "mpi_job_horovod.yaml",
    }

    if extra_bai_config_args is None:
        extra_bai_config_args = {}

    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, os.pardir, "templates")

    with open(os.path.join(templates_dir, template_files[descriptor.strategy]), "r") as f:
        contents = f.read()
    config_template = ConfigTemplate(contents)
    bai_config = BaiConfig(descriptor, config_template, **extra_bai_config_args)

    if descriptor.strategy == 'single_node':
        bai_config.add_benchmark_cmd_to_container()
    elif descriptor.strategy == 'horovod':
        bai_config.add_benchmark_cmd_to_config_map()
    else:
        raise ValueError("Unsupported configuration at transpiler")

    return bai_config
