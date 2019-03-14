import toml
import argparse
import os
import sys
import uuid

import ruamel.yaml as yaml

from kubernetes import client
from urllib.parse import urlparse
from typing import Dict, List


class Descriptor:
    """
    The model class for a Descriptor.
    It validates and contains all data the descriptor contains.
    """

    VALID_DATA_SOURCES = ['s3', 'http', 'https', 'ftp', 'ftps']

    def __init__(self, toml_file: str):
        """
        Constructor
        :param toml_file: TOML descriptor file path
        """
        descriptor_toml = toml.load(toml_file)

        try:
            self.instance_type = descriptor_toml['hardware']['instance_type']
            self.docker_image = descriptor_toml['env']['docker_image']
            self.benchmark_code = descriptor_toml['ml']['benchmark_code']
        except KeyError as e:
            raise KeyError('Required field is missing in the descriptor toml file') from e

        self.extended_shm = descriptor_toml['env'].get('extended_shm', False)
        self.privileged = descriptor_toml['env'].get('privileged', False)
        self.ml_args = descriptor_toml['ml'].get('args', '')

        # TODO: What if there is no data section?
        if 'data' in descriptor_toml:
            self.dataset = descriptor_toml['data']['id']
            self.data_sources = self._process_data_sources(descriptor_toml['data'].get('sources', []))

        self._validate()

    def _validate(self):
        """
        Validates that this descriptor is valid
        """
        for source in self.data_sources:
            assert source.get('uri', ''), 'Missing data uri'
            assert source['scheme'] in self.VALID_DATA_SOURCES, f'Invalid data uri: {source["uri"]}'

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
            print(f'{origin} not supported as a data source yet')


class BaiConfig:
    MOUNT_CHMOD = '777'
    SHARED_MEMORY_VOL = 'dshm'

    # TODO: Figure out how to coordinate fetcher and puller
    S3_REGION = 'eu-west-1'
    PULLER_IMAGE = 'stsukrov/s3dataprovider'

    def __init__(self, descriptor: Descriptor):
        """
        Reads the values from the descriptor file into a settings dictionary
        :param descriptor: Descriptor object with the information from the TOML
        :return:
        """
        self.descriptor = descriptor

        self.job_id = uuid.uuid4().hex
        self.container_args = self._get_container_args()
        self.data_volumes = self._get_data_volumes()
        self.pod_spec_volumes = self._get_pod_spec_volumes(self.data_volumes)
        self.pod_spec_init_containers = self._get_data_puller(self.data_volumes, descriptor.data_sources)
        self.container_volume_mounts = self._get_container_volume_mounts()

    def _get_container_args(self) -> str:
        """
        Extracts the args for the container and formats them.
        :return: the container's args
        """
        return self.descriptor.benchmark_code + ' ' + self.descriptor.ml_args + ';'

    def _get_data_volumes(self) -> Dict:
        data_sources = self.descriptor.data_sources
        # Data destination paths and the corresponding mounted vols
        destination_paths = set([s['path'] for s in data_sources])
        data_vols = {}

        for idx, dest in enumerate(destination_paths):
            name = 'p' + str(idx)
            puller_path = f'/data/{name}'
            data_vols[dest] = {'name': name,
                               'puller_path': puller_path}

        return data_vols

    def _get_pod_spec_volumes(self, data_volumes):
        volumes = []

        if self.descriptor.extended_shm:
            shm = client.V1Volume(name=self.SHARED_MEMORY_VOL,
                                  empty_dir=client.V1EmptyDirVolumeSource(medium="Memory"))
            volumes.append(shm.to_dict())

        for vol in data_volumes.values():
            volumes.append(client.V1Volume(name=vol['name'],
                                           empty_dir=client.V1EmptyDirVolumeSource())
                           .to_dict())

        return self.remove_null_entries(volumes)

    def _get_container_volume_mounts(self) -> List:
        vol_mounts = []

        if self.descriptor.extended_shm:
            vol_mounts.append(client.V1VolumeMount(name=self.SHARED_MEMORY_VOL,
                                                   mount_path='/dev/shm')
                              .to_dict())

        for dest_path, vol in self.data_volumes.items():
            vol_mounts.append(client.V1VolumeMount(name=vol['name'],
                                                   mount_path=dest_path)
                              .to_dict())

        return self.remove_null_entries(vol_mounts)

    def _get_puller_volume_mounts(self, data_volumes) -> List:
        vol_mounts = []

        for vol in data_volumes.values():
            vol_mounts.append(client.V1VolumeMount(name=vol['name'],
                                                   mount_path=vol['puller_path'])
                              .to_dict())

        return vol_mounts

    def _get_data_puller(self, data_volumes, data_sources):
        """
        Extracts the args for the data puller container and formats them.
        :return: dict with the puller object
        """
        if not data_sources:
            return {}

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
        puller = client.V1Container(name='data-puller',
                                    image=self.PULLER_IMAGE,
                                    args=puller_args,
                                    volume_mounts=vol_mounts)
        return self.remove_null_entries(puller.to_dict())

    def remove_null_entries(self, d):
        """
        Remove entries with null values from the dict or list passed as parameter.
        """
        # This method is needed because k8s client objects.to_dict() contain many Null fields
        if not isinstance(d, (dict, list)):
            return d
        if isinstance(d, list):
            return [v for v in (self.remove_null_entries(v) for v in d) if v is not None]
        return {k: v for k, v in ((k, self.remove_null_entries(v)) for k, v in d.items()) if v is not None}

    def get_full_dict(self) -> Dict:
        """
        :return: dict with all attributes of the BaiConfig and its Descriptor
        """
        bai_config_dict = vars(self).copy()
        bai_config_dict.pop('descriptor')
        return {**vars(self.descriptor), **bai_config_dict}


class ConfigTemplate:
    def __init__(self, template_file: str):
        with open(template_file, "r") as f:
            self.config_template_string = f.read()

    def _replace_templated_fields(self, d: Dict, templates: Dict[str, Dict]):
        """
        Iterates through the dict passed as parameter and replaces all templated fields with
        the corresponding values.
        :param d: dictionary containing values which need replacement
        :param templates: dict[str, dict] which holds the replacement values
        """
        if hasattr(d, 'items'):
            for k, v in d.copy().items():
                if self._is_templated_field(v):
                    field_name = v[1:-1]  # Remove < >
                    d[k] = templates[field_name]
                if isinstance(v, dict):
                    self._replace_templated_fields(v, templates)
                elif isinstance(v, list):
                    for elem in v:
                        self._replace_templated_fields(elem, templates)

    def _is_templated_field(self, val) -> bool:
        return isinstance(val, str) and val.startswith('<') and val.endswith('>')

    def dump_yaml_string(self, settings: Dict, output_stream):
        """
        Fill in the template with the given configuration and print the result, either to stdout
        or to a file.
        :param settings: dict[field_to_replace:str, value]
        :param output_stream:
        """
        formatted_config = self.config_template_string.format(**settings)
        config_dict = yaml.load(formatted_config, Loader=yaml.RoundTripLoader)
        self._replace_templated_fields(config_dict, settings)

        yaml.dump(config_dict, output_stream, Dumper=yaml.RoundTripDumper)


def main():
    parser = argparse.ArgumentParser(description='Reads the descriptor file and creates the '
                                                 'corresponding job config yaml file.')

    parser.add_argument('descriptor',
                        help='Relative path to descriptor file')

    parser.add_argument('--template',
                        help='Path to job config template file',
                        default='job_config_template.yaml')

    parser.add_argument('-f', '--filename', metavar='filename', nargs='?',
                        help='Output to file. If not specified, output to stdout',
                        default=None,
                        const='job_config.yaml')

    args = parser.parse_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))

    job_config_template = ConfigTemplate(os.path.join(current_dir, args.template))
    descriptor = Descriptor(args.descriptor)
    bai_config = BaiConfig(descriptor)

    if getattr(args, "filename"):
        output_stream = open(os.path.join(current_dir, args.filename), 'w')
    else:
        output_stream = sys.stdout

    job_config_template.dump_yaml_string(bai_config.get_full_dict(), output_stream)

    if not output_stream == sys.stdout:
        output_stream.close()


if __name__ == '__main__':
    main()
