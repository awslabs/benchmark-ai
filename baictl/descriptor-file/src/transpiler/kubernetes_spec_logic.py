import addict
import itertools

import ruamel.yaml as yaml

from typing import Dict

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
ConfigMap = addict.Dict


class KubernetesRootObjectHelper:
    """
    A wrapper for the top-level Kubernetes object.

    It provides serialization/deserialization from YAML and utility methods to make its usage easier.

    The yaml file is loaded/dumped using RoundTripLoader and RoundTripDumper to preserve the order of fields.
    While it doesn't break anything, it keeps the generated yaml closer to the input template.
    """
    def __init__(self, contents: str):
        """
        :param contents: The parsed YAML contents of a full Kubernetes object, as a Dict
        """
        docs = yaml.load_all(contents, Loader=yaml.RoundTripLoader)
        self.config_maps = []

        # TODO: Improve generalization here
        for d in docs:
            if d['kind'] == 'ConfigMap':
                self.config_maps.append(addict.Dict(d))
            elif d['kind'] in ['Job', 'MPIJob']:
                self._root = addict.Dict(d)

        self._validate()

        # Create empty fields if required
        if not self.get_pod_spec().initContainers:
            self.get_pod_spec().initContainers = []
        if not self.get_pod_spec().volumes:
            self.get_pod_spec().volumes = []
        for container in self.get_pod_spec().containers:
            if not container.volumeMounts:
                container.volumeMounts = []

    def _validate(self):
        if not self._root.spec:
            raise ValueError("Spec of root object not found at yaml definition of the Kubernetes object")
        if not self.get_pod_spec():
            raise ValueError("Pod not found at yaml definition of the Kubernetes object")
        if not self.get_pod_spec().containers:
            raise ValueError("A Pod must have at least 1 container on its definition")

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
        init_containers = self.get_pod_spec().initContainers
        for container in itertools.chain(containers, init_containers):
            if container.name == container_name:
                return container
        raise ValueError("Container {} not found. Available containers are: {}".format(
            container_name,
            [c.name for c in itertools.chain(containers, init_containers)]
        ))

    def remove_container(self, container_name: str):
        """
        Removes a given container (can be an initContainer)
        :param container_name: The name of the container
        :raises: ValueError if the container could not be found
        """
        containers = self.get_pod_spec().containers
        init_containers = self.get_pod_spec().initContainers

        for container_list in [containers, init_containers]:
            for container in container_list:
                if container.name == container_name:
                    container_list.remove(container)
                    return

        raise ValueError("Container {} not found. Available containers are: {}".format(
            container_name,
            [c.name for c in itertools.chain(containers, init_containers)]
        ))

    def find_config_map(self, name) -> ConfigMap:
        for cm in self.config_maps:
            if cm.metadata.name == name:
                return cm
        raise ValueError("ConfigMap {} not found. Available ones are: {}".format(
            name,
            [cm.metadata.name for cm in self.config_maps]
        ))

    def to_yaml(self) -> str:
        """
        Serializes this object to a YAML string

        :return: the yaml string
        """
        root_as_dict = self._root.to_dict()
        config_maps_as_dicts = [cm.to_dict() for cm in self.config_maps]
        return yaml.dump_all(itertools.chain(config_maps_as_dicts, [root_as_dict]), Dumper=yaml.RoundTripDumper)


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

    def build(self):
        contents = self._yaml_template_contents.format(**self._variables)
        return KubernetesRootObjectHelper(contents)

