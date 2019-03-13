import toml
import argparse
import os
import sys
import uuid

import ruamel.yaml as yaml

from kubernetes import client
from urllib.parse import urlparse
from typing import Dict, List


class DescriptorReader:

    VALID_DATA_SOURCES = ['s3', 'http', 'https', 'ftp', 'ftps']
    MOUNT_CHMOD = '777'
    SHARED_MEMORY_VOL = 'dshm'

    # TODO: Figure out how to coordinate fetcher and puller
    S3_REGION = 'eu-west-1'
    PULLER_IMAGE = 'stsukrov/s3dataprovider'

    def __init__(self, descriptor_path: str):
        """
        Reads the values from the descriptor file into a settings dictionary
        :param descriptor_path: path to the descriptor file
        :return:
        """
        descriptor = toml.load(descriptor_path)
        try:
            self.settings = {
                'instance_type': descriptor['hardware']['instance_type'],
                'docker_image': descriptor['env']['docker_image'],
                'extended_shm': descriptor['env']['extended_shm'],
                'benchmark_code': descriptor['ml']['benchmark_code'],
            }
        except KeyError as e:
            raise KeyError('Required field is missing in the descriptor file') from e

        self.settings['privileged'] = descriptor['env'].get("privileged", False)

        if 'args' in descriptor['ml']:
            self.settings['ml_args'] = descriptor['ml']['args']

        if 'data' in descriptor:
            self.settings['dataset'] = descriptor['data']['id']
            if 'sources' in descriptor['data']:
                self.settings['data_sources'] = descriptor['data']['sources']
                self.settings['data_volumes'] = self._get_data_volumes()

        # TODO: Verify there are K8s labels to store info such as dataset, docker_image, instance_type...
        job_id = uuid.uuid4().hex
        self.settings['job_id'] = job_id
        self.settings['container_name'] = 'benchmark'
        self.settings['container_args'] = self._get_container_args()

        self.settings['templates'] = {
            'pod_spec_volumes': self._get_pod_spec_volumes(),
            'pod_spec_init_containers': self._get_data_puller(),
            'container_volume_mounts': self._get_container_volume_mounts()
        }

    def fill_template(self, template: str) -> str:
        """
        Fill in the job config file
        :param template: str with the job config template
        :return: job config string
        """
        config_dict = yaml.load(template.format(**self.settings), Loader=yaml.RoundTripLoader)
        self._replace_templated_fields(config_dict, self.settings['templates'])

        return config_dict

    def _get_container_args(self) -> str:
        """
        Extracts the args for the container and formats them.
        :return: the container's args
        """
        cmd = self.settings['benchmark_code']

        if 'ml_args' in self.settings:
            cmd += ' ' + self.settings['ml_args']

        return cmd + ';'

    def _get_data_volumes(self) -> Dict:
        data_sources = self.settings['data_sources']
        # Data destination paths and the corresponding mounted vols
        destination_paths = {[s['path'] for s in data_sources]}
        data_vols = {}

        for idx, dest in enumerate(destination_paths):
            name = 'p' + str(idx)
            puller_path = f'/data/{name}'
            data_vols[dest] = {'name': name,
                               'puller_path': puller_path}

        return data_vols

    def _get_pod_spec_volumes(self):
        volumes = []

        if 'extended_shm' in self.settings:
            shm = client.V1Volume(name=self.SHARED_MEMORY_VOL,
                                  empty_dir=client.V1EmptyDirVolumeSource(medium="Memory"))
            volumes.append(shm.to_dict())

        if 'data_volumes' in self.settings:
            for _, vol in self.settings['data_volumes'].items():
                volumes.append(client.V1Volume(name=vol['name'],
                                               empty_dir=client.V1EmptyDirVolumeSource())
                               .to_dict())

        return remove_null_entries(volumes)

    def _get_container_volume_mounts(self) -> List:
        vol_mounts = []

        if 'extended_shm' in self.settings:
            vol_mounts.append(client.V1VolumeMount(name=self.SHARED_MEMORY_VOL,
                                                   mount_path='/dev/shm')
                              .to_dict())

        for dest_path, vol in self.settings['data_volumes'].items():
            vol_mounts.append(client.V1VolumeMount(name=vol['name'],
                                                   mount_path=dest_path)
                              .to_dict())

        return remove_null_entries(vol_mounts)

    def _get_puller_volume_mounts(self) -> List:
        vol_mounts = []

        for _, vol in self.settings['data_volumes'].items():
            vol_mounts.append(client.V1VolumeMount(name=vol['name'],
                                                   mount_path=vol['puller_path'])
                              .to_dict())

        return vol_mounts

    def _get_data_puller(self):
        """
        Extracts the args for the data puller container and formats them.
        :return: dict with the puller object
        """
        processed_sources = []
        try:
            for source in self.settings['data_sources']:
                uri_components = self._process_uri(source['uri'])
                processed_sources.append({**source, **uri_components})
        except KeyError as e:
            raise KeyError('Required field is missing in the descriptor file.'
                           ' Each data source must have a download uri and a destination path.') from e
        except ValueError as e:
            raise ValueError('Incorrect download URI.') from e

        # Placeholder until the data fetcher is ready
        # ------------------------------------------
        unique_buckets = set([s['bucket'] for s in processed_sources])

        if len(unique_buckets) != 1:
            raise ValueError('Too many different S3 buckets to pull from (only one is allowed at the moment)')

        bucket = unique_buckets.pop()

        s3_objects = []
        for s in processed_sources:
            s3_objects.append(s['object'] + ',' +
                              self.MOUNT_CHMOD + ',' +
                              self.settings['data_volumes'][s['path']]['name'])

        puller_args = [self.S3_REGION, bucket, ':'.join(s3_objects)]
        # ------------------------------------------

        vol_mounts = self._get_puller_volume_mounts()
        puller = client.V1Container(name='data-puller',
                                    image=self.PULLER_IMAGE,
                                    args=puller_args,
                                    volume_mounts=vol_mounts).to_dict()
        return remove_null_entries(puller)

    def _process_uri(self, uri):
        """
        Handles a data URI to extract the relevant information.
        :param uri: str starting with the source, such as s3://bucket/object-name
        :return: dict with the relevant information
        """
        parsed = urlparse(uri)
        if parsed.scheme not in self.VALID_DATA_SOURCES:
            raise ValueError(f'Data source uri must start with one of the following:'
                             f' {a+":// " for a in self.VALID_DATA_SOURCES}')
        if parsed.scheme == 's3':
            return {'source': parsed.scheme, 'bucket': parsed.netloc, 'object': parsed.path}

        # TODO: Add data sources other than S3
        else:
            print(f'{origin} not supported as a data source yet')

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


def main():
    parser = argparse.ArgumentParser(description='Reads the descriptor file and creates the '
                                                 'corresponding job config yaml file.')

    parser.add_argument('descriptor',
                        help='Relative path to descriptor file')

    parser.add_argument('--template',
                        help='Path to job config template file',
                        default='job_config_template.yaml')

    parser.add_argument('-f', metavar='outfile', nargs='?',
                        help='Output to file. If not specified, output to stdout',
                        default=None,
                        const='job_config.yaml')

    args = parser.parse_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, args.template), 'r') as stream:
        template = stream.read()

    reader = DescriptorReader(args.descriptor)
    job_config = reader.fill_template(template)

    if args.f:
        with open(os.path.join(current_dir, args.f), 'w') as outfile:
            yaml.dump(job_config, outfile, Dumper=yaml.RoundTripDumper)
    else:
        yaml.dump(job_config, sys.stdout, Dumper=yaml.RoundTripDumper)


if __name__ == '__main__':
    main()
