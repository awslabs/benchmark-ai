import random

import logging
import toml
import argparse
import os
import uuid
import addict
import shlex

import ruamel.yaml as yaml

from urllib.parse import urlparse
from typing import Dict, List, Optional

# Using the official Kubernetes Model classes (https://github.com/kubernetes-client/python) is avoided here
# because it presents some problems:
#
# 1) Custom Resource Definitions (eg.: kubeflow)
#       => This is a BLOCKER for why it is not a good idea to use the python-client as the provider for the model
#       classes.
#
# 2) When using the to_dict() of the classes, that is not a valid Kubernetes yaml since it outputs the fields as
#   snake_case and not camelCase as expected by the Kubernetes API.
#       => This can be fixed with a workaround, so it is just an annoying fact.
#
# 3) Hacky way to create the class from a YAML object.
#        => There is no clean way to create a Kubernetes model object from a yaml file without going through the
#        internals of the Python client API.
#        The closest method is `create_from_yaml()`, which is analogous to `kubectl apply -f file.yaml`, which:
#        - calls the K8S Api server with the contents of the yaml.
#        - returns the results as a Kubernetes Model object by deserializing the response.
#
#        Diving into the `create_from_yaml()` method I found this `deserialize()` method, which can create the objects
#        correctly. However it requires a JSON as input and also the type it must create:
#
#            def deserialize(self, response, response_type) -> response_type:
#               return self.__deserialize(json.load(response.data), response_type)
#
#        The theory is that these Kubernetes Model objects were not made for being manipulated as real model objects,
#        but only for having a "type-safe" way of interacting with the responses of the Kubernetes server.

# Some types so we can use type annotations to make the code more readable.
# While doing this doesn't give any form of static typing, it helps show intention, which is better than nothing.
# It wouldn't be an issue if we could use the official Kubernetes Model classes, however, that's not possible due to
# the reasons stated above.
Container = addict.Dict
PodSpec = addict.Dict
VolumeMount = addict.Dict
Job = addict.Dict
Volume = addict.Dict
EmptyDirVolumeSource = addict.Dict
HostPath = addict.Dict


class Descriptor:
    """
    The model class for a Descriptor.
    It validates and contains all data the descriptor contains.
    """

    VALID_DATA_SOURCES = ['s3', 'http', 'https', 'ftp', 'ftps']
    VALID_STRATEGIES = ['horovod']

    def __init__(self, descriptor_data: Dict):
        """
        Constructor
        :param data: dict contaning the data as loaded from the descriptor toml file
        """
        try:
            self.instance_type = descriptor_data['hardware']['instance_type']
            self.docker_image = descriptor_data['env']['docker_image']
        except KeyError as e:
            raise KeyError('Required field is missing in the descriptor toml file') from e

        self.distributed = 'distributed' in descriptor_data['hardware']
        distributed_data = descriptor_data['hardware'].get('distributed', {})
        self.num_instances = distributed_data.get('num_instances', 1)
        self.gpus_per_instance = distributed_data.get('gpus_per_instance', 1)
        self.distributed_strategy = distributed_data.get('strategy', '')

        self.extended_shm = descriptor_data['env'].get('extended_shm', False)
        self.privileged = descriptor_data['env'].get('privileged', False)
        self.benchmark_code = descriptor_data['ml'].get('benchmark_code', '')
        self.ml_args = descriptor_data['ml'].get('args', '')

        self.dataset = descriptor_data.get('data', {}).get('id', '')
        descriptor_sources = descriptor_data.get('data', {}).get('sources', [])
        self.data_sources = self._process_data_sources(descriptor_sources)

        self._validate()

    @classmethod
    def from_toml_file(cls, toml_file: str):
        """
        Constructor from toml file path
        :param toml_file: TOML descriptor file path
        :return:
        """
        descriptor_toml = toml.load(toml_file)
        return Descriptor(descriptor_toml)

    def _validate(self):
        """
        Validates that this descriptor is valid
        """
        for source in self.data_sources:
            if not source.get('uri', ''):
                raise ValueError('Missing data uri')
            if source['scheme'] not in self.VALID_DATA_SOURCES:
                raise ValueError(f'Invalid data uri: {source["uri"]}')

        if self.distributed:
            if self.num_instances <= 1:
                logging.warning(f'Specified a distributed strategy but using {self.num_instances} nodes')
            if self.distributed_strategy not in self.VALID_STRATEGIES:
                raise ValueError(f'Invalid distributed strategy: {self.distributed_strategy}')

        # TODO: Validate the chosen instance type has enough GPUs

    def _process_data_sources(self, data_sources: List) -> List:
        processed_sources = []

        for source in data_sources:
            uri_components = self._process_uri(source.get('uri', ''))
            processed_sources.append({**source, **uri_components})

        return processed_sources

    def _process_uri(self, uri):
        """
        Handles a data URI to extract the relevant information.
        :param uri: str starting with the source, such as s3://bucket/object-name
        :return: dict with the relevant information
        """
        parsed = urlparse(uri)

        if parsed.scheme == 's3':
            return {'scheme': parsed.scheme, 'bucket': parsed.netloc, 'object': parsed.path[1:]}

        # TODO: Add data sources other than S3
        else:
            raise ValueError(f'{parsed.scheme} not supported as a data source yet')


class KubernetesHelper:
    """
    A wrapper for the top-level Kubernetes object.

    It provides serialization/deserialization from YAML. Utility methods are provided by extensions of this class.

    The yaml file is loaded/dumped using RoundTripLoader and RoundTripDumper to preserve the order of fields.
    While it doesn't break anything, it keeps the generated yaml closer to the input template.
    """
    def __init__(self, contents: str):
        yaml_data = yaml.load(contents, Loader=yaml.RoundTripLoader)
        self._root = addict.Dict(yaml_data)

    def get_metadata(self):
        return self._root.metadata

    def to_yaml(self) -> str:
        """
        Serializes this object to a YAML string

        :return: the yaml string
        """
        root_as_dict = self.to_dict()
        return yaml.dump(root_as_dict, Dumper=yaml.RoundTripDumper)

    def to_dict(self):
        def remove_null_entries(d):
            """
            Remove entries with null values from the dict or list passed as parameter.
            """
            # This method is needed because k8s client objects.to_dict() contain many Null fields
            if not isinstance(d, (dict, list)):
                return d
            if isinstance(d, list):
                return [v for v in (remove_null_entries(v) for v in d) if v is not None]
            return {k: v for k, v in ((k, remove_null_entries(v)) for k, v in d.items()) if v is not None}

        root_as_dict = self._root.to_dict()
        return remove_null_entries(root_as_dict)


class KubernetesRootObjectHelper(KubernetesHelper):
    """
    Extension of the KubernetesHelper to handle root objects such as Jobs or MPIJobs.

    It provides some utility methods to make it easier to work with them.
    """
    def __init__(self, contents: str):
        """
        :param contents: The YAML contents of a full Kubernetes object
        """
        super().__init__(contents)

        # Validation
        if not self._root.spec:
            raise ValueError("Spec of root object not found at yaml definition of the Kubernetes object")
        if not self.get_pod_spec():
            raise ValueError("Pod not found at yaml definition of the Kubernetes object")
        containers = self.get_pod_spec().containers
        if not containers:
            raise ValueError("A Pod must have at least 1 container on its definition")

        # Create empty fields if required
        if not self.get_pod_spec().initContainers:
            self.get_pod_spec().initContainers = []
        if not self.get_pod_spec().volumes:
            self.get_pod_spec().volumes = []
        for container in self.get_pod_spec().containers:
            if not container.volumeMounts:
                container.volumeMounts = []

    def get_pod_spec(self) -> PodSpec:
        return self._root.spec.template.spec

    def find_container(self, container_name: str) -> Container:
        """
        Finds a given container (can be an initContainer)
        :param container_name: The name of the container
        :return: The container object
        :raises: ValueError if the container could not be found
        """
        containers = self.get_pod_spec().containers
        initContainers = self.get_pod_spec().initContainers
        for container in containers + initContainers:
            if container.name == container_name:
                return container
        raise ValueError("Container {} not found. Available containers are: {}".format(
            container_name,
            [c.name for c in containers]
        ))


class ConfigTemplate:
    """
    A wrapper for the yaml template file.

    This class adds support to being able to use str.format() fields in the contents
    of the yaml. The values of these fields are provided through the `feed()` method.
    """

    def __init__(self, yaml_template_contents: str):
        self._yaml_template_contents = yaml_template_contents
        self._variables = {}

    def feed(self, variables: Dict[str, str]):
        self._variables.update(variables)

    def get_contents(self):
        return self._yaml_template_contents.format(**self._variables)

    def get_docs(self) -> List:
        # YAML docs are separated by '---'
        return self.get_contents().split('---')

    def build_root(self) -> KubernetesRootObjectHelper:
        """
        Builds the Kubernetes root object
        :return:
        """
        # We expect all documents to be ConfigMaps except for the last one
        return KubernetesRootObjectHelper(self.get_docs()[-1])

    def build_config_maps(self) -> List[KubernetesHelper]:
        return [KubernetesHelper(doc) for doc in self.get_docs()[:-1]]


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
        Reads the values from the descriptor file into a settings dictionary
        :param descriptor: Descriptor object with the information from the TOML
        :param config_template: The YAML template
        :param random_object: An instance of random.Random [optional].
                              This field exists mostly to facilitate testing so that predictable random data is
                              generated.
        """
        self.descriptor = descriptor

        if random_object is None:
            random_object = random.Random()

        config_template.feed(vars(self.descriptor))
        config_template.feed(
            {
             # random_object.getrandbits(128) is equivalent to os.urandom(16), since 16 * 8 = 128
             "job_id": uuid.UUID(int=random_object.getrandbits(128), version=4).hex}
        )
        self.root = config_template.build_root()

        self.config_maps = config_template.build_config_maps()
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
        root_yaml = self.root.to_yaml()
        if self.config_maps:
            # Get the yaml for each of the docs and concatenate them again
            config_map_yamls = [m.to_yaml() for m in self.config_maps]
            return '\n---\n'.join(config_map_yamls + [root_yaml])
        return root_yaml

    def add_benchmark_cmd_to_container(self):
        """
        Extracts the command and args for the benchmark container, formats them and inserts them.
        The command is split into args and passed to the container as a list.
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

    def add_benchmark_cmd_to_config_map(self):
        """
        Adds the benchmark code and args to the entrypoint configmap.
        """
        def find_config_map(name) -> KubernetesHelper:
            for cm in self.config_maps:
                if cm.get_metadata().name.startswith(name):
                    return cm

        if self.descriptor.benchmark_code:
            benchmark_cmd = self.descriptor.benchmark_code + self.descriptor.ml_args
            # Using yaml.PreservedScalarString so multiline strings are printed properly
            benchmark_cmd = yaml.scalarstring.PreservedScalarString(benchmark_cmd)

            entrypoint_config_map = find_config_map('entrypoint')
            entrypoint_config_map._root.data.entrypoint = benchmark_cmd

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
        Extracts the args for the data puller container and formats them.

        :return: The puller container object
        """
        if not data_sources:
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

    :param descriptor: The descriptor.
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
    strategy = descriptor.distributed_strategy or 'single_node'

    with open(os.path.join(current_dir, "templates", template_files[strategy]), "r") as f:
        contents = f.read()
    config_template = ConfigTemplate(contents)
    bai_config = BaiConfig(descriptor, config_template, **extra_bai_config_args)

    if strategy == 'single_node':
        bai_config.add_benchmark_cmd_to_container()
    elif strategy == 'horovod':
        bai_config.add_benchmark_cmd_to_config_map()

    return bai_config

    # # TODO: Improve this error message
    # raise ValueError("Unsupported configuration at descriptor")


def main():
    parser = argparse.ArgumentParser(description='Reads the descriptor file and creates the '
                                                 'corresponding job config yaml file.')

    parser.add_argument('descriptor',
                        help='Relative path to descriptor file')

    parser.add_argument('-f', '--filename', metavar='filename', nargs='?',
                        help='Output to file. If not specified, output to stdout',
                        default=None,
                        const='job_config.yaml')

    args = parser.parse_args()

    descriptor = Descriptor.from_toml_file(args.descriptor)
    bai_config = create_bai_config(descriptor)
    yaml_string = bai_config.dump_yaml_string()

    if args.filename:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, args.filename), 'w') as f:
            f.write(yaml_string)
    else:
        print(yaml_string)


if __name__ == '__main__':
    main()
