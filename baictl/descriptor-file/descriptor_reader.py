import random

import toml
import argparse
import os
import uuid
import yaml
import addict

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


class Descriptor:
    """
    The model class for a Descriptor.
    It validates and contains all data the descriptor contains.
    """

    VALID_DATA_SOURCES = ['s3', 'http', 'https', 'ftp', 'ftps']

    def __init__(self, descriptor_data: Dict):
        """
        Constructor
        :param data: dict contaning the data as loaded from the descriptor toml file
        """
        try:
            self.instance_type = descriptor_data['hardware']['instance_type']
            self.docker_image = descriptor_data['env']['docker_image']
            self.benchmark_code = descriptor_data['ml']['benchmark_code']
        except KeyError as e:
            raise KeyError('Required field is missing in the descriptor toml file') from e

        self.single_node = True
        self.extended_shm = descriptor_data['env'].get('extended_shm', False)
        self.privileged = descriptor_data['env'].get('privileged', False)
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
            return {'scheme': parsed.scheme, 'bucket': parsed.netloc, 'object': parsed.path}

        # TODO: Add data sources other than S3
        else:
            raise ValueError(f'{origin} not supported as a data source yet')


class KubernetesRootObjectHelper:
    """
    A wrapper for the top-level Kubernetes object.

    It provides some utility methods and serialization/deserialization from YAML.
    """
    def __init__(self, contents: str):
        """
        :param contents: The YAML contents of a full Kubernetes object
        """
        yaml_data = yaml.safe_load(contents)
        self._root = addict.Dict(yaml_data)

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
        :param container_name: The name of the container
        :return: The container object
        :raises: ValueError if the container could not be found
        """
        containers = self.get_pod_spec().containers
        for container in containers:
            if container.name == container_name:
                return container
        raise ValueError("Container {} not found. Available containers are: {}".format(
            container_name,
            [c.name for c in containers]
        ))

    def to_yaml(self) -> str:
        """
        Serializes this object to a YAML string

        :return: the yaml string
        """
        root_as_dict = self.to_dict()
        # Don't use self.root.to_str() because it uses pretty printing under the hood.
        # Using the yaml module gives better guarantees.
        return yaml.dump(root_as_dict)

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

    def build_root(self) -> KubernetesRootObjectHelper:
        """
        :return:
        """
        contents = self._yaml_template_contents.format(**self._variables)
        return KubernetesRootObjectHelper(contents)


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
            {"container_args": self._get_container_args(),
             # random_object.getrandbits(128) is equivalent to os.urandom(16), since 16 * 8 = 128
             "job_id": uuid.UUID(int=random_object.getrandbits(128), version=4).hex}
        )
        self.root = config_template.build_root()
        self.add_volumes()

    def add_volumes(self):
        data_volumes = self._get_data_volumes(self.descriptor.data_sources)

        benchmark_container = self.root.find_container("benchmark")
        benchmark_container.volumeMounts.extend(self._get_container_volume_mounts(data_volumes))

        pod_spec = self.root.get_pod_spec()
        data_puller = self._get_data_puller(data_volumes, self.descriptor.data_sources)
        if data_puller is not None:
            pod_spec.initContainers.append(data_puller)
        pod_spec.volumes.extend(self._get_pod_spec_volumes(data_volumes))

    def dump_yaml_string(self):
        return self.root.to_yaml()

    def _get_container_args(self) -> str:
        """
        Extracts the args for the container and formats them.
        :return: the container's args
        """
        return self.descriptor.benchmark_code + ' ' + self.descriptor.ml_args + ';'

    def _get_data_volumes(self, data_sources: List) -> Dict:
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

        if self.descriptor.extended_shm:
            shm = Volume(name=self.SHARED_MEMORY_VOL,
                         emptyDir=EmptyDirVolumeSource(medium="Memory"))
            d = shm.to_dict()
            volumes.append(d)

        for vol in data_volumes.values():
            volumes.append(Volume(name=vol['name'],
                                  emptyDir=EmptyDirVolumeSource()))

        return volumes

    def _get_container_volume_mounts(self, data_volumes) -> List[VolumeMount]:
        vol_mounts = []

        if self.descriptor.extended_shm:
            vol_mounts.append(VolumeMount(name=self.SHARED_MEMORY_VOL,
                                          mountPath='/dev/shm'))

        for dest_path, vol in data_volumes.items():
            vol_mounts.append(VolumeMount(name=vol['name'],
                                          mountPath=dest_path))
        return vol_mounts

    def _get_data_puller(self, data_volumes, data_sources) -> Optional[Container]:
        """
        Extracts the args for the data puller container and formats them.

        :return: The puller container object
        """
        if not data_sources:
            return None

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
        puller = Container(name='data-puller',
                           image=self.PULLER_IMAGE,
                           args=puller_args,
                           volumeMounts=vol_mounts)
        return puller

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
    if extra_bai_config_args is None:
        extra_bai_config_args = {}

    current_dir = os.path.dirname(os.path.abspath(__file__))
    if descriptor.single_node:
        with open(os.path.join(current_dir, "job_config_template.yaml"), "r") as f:
            contents = f.read()
        config_template = ConfigTemplate(contents)
        bai_config = BaiConfig(descriptor, config_template, **extra_bai_config_args)
        return bai_config

    # TODO: Improve this error message
    raise ValueError("Unsupported configuration at descriptor")


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
