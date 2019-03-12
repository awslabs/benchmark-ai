import toml
import argparse
import os
import sys
import uuid

import kubernetes as k8s
import ruamel.yaml as yaml

from typing import Dict, List


VALID_DATA_SOURCES = ['s3', 'http', 'https', 'ftp']
MOUNT_CHMOD = '777'
SHARED_MEMORY_VOL = 'dshm'

S3_REGION = 'eu-west-1'  # TODO: Move to descriptor
PULLER_IMAGE = 'stsukrov/s3dataprovider'  # TODO: Extend to support different types of pullers


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

    settings = read_descriptor(args.descriptor)
    job_config = fill_template(settings, template)

    if args.f:
        with open(os.path.join(current_dir, args.f), 'w') as outfile:
            yaml.dump(job_config, outfile, Dumper=yaml.RoundTripDumper)
    else:
        yaml.dump(job_config, sys.stdout, Dumper=yaml.RoundTripDumper)


def read_descriptor(descriptor_path: str) -> Dict[str, str]:
    """
    Reads the values from the descriptor file into a dictionary
    :param descriptor_path: path to the descriptor file
    :return:
    """
    descriptor = toml.load(descriptor_path)

    try:
        settings = {
            'instance_type': descriptor['hardware']['instance_type'],
            'docker_image': descriptor['env']['docker_image'],
            'extended_shm': descriptor['env']['extended_shm'],
            'benchmark_code': descriptor['ml']['benchmark_code'],
        }
    except KeyError as e:
        raise KeyError('Required field is missing in the descriptor file') from e

    if 'args' in descriptor['ml']:
        settings['ml_args'] = descriptor['ml']['args']

    settings['privileged'] = False if 'privileged' not in settings['env'] else settings['env']['privileged']

    if 'data' in descriptor:
        settings['dataset'] = descriptor['data']['id']
        if 'sources' in descriptor['data']:
            settings['data_sources'] = descriptor['data']['sources']

    return settings


def fill_template(settings: Dict, template: str) -> str:
    """
    Fill in the job config file
    :param settings: dict with the parsed input from the descriptor file
    :param template: str with the job config template
    :return: job config string
    """
    # TODO: Verify there are K8s labels to store info such as dataset, docker_image, instance_type...
    job_id = uuid.uuid4().hex
    settings['job_id'] = job_id
    settings['container_name'] = job_id
    settings['container_args'] = get_container_args(settings)

    if 'data_sources' in settings:
        settings['data_volumes'] = get_data_volumes(settings['data_sources'])

    settings['templates'] = {
        'pod_spec_volumes': get_pod_spec_volumes(settings),
        'pod_spec_init_containers': get_data_puller(settings),
        'container_volume_mounts': get_container_volume_mounts(settings)
    }

    config_dict = yaml.load(template.format(**settings), Loader=yaml.RoundTripLoader)
    replace_templated_fields(config_dict, settings['templates'])

    return config_dict


def get_container_args(settings: Dict[str, str]) -> str:
    """
    Extracts the args for the container and formats them.
    :param settings: dict containing the parsed input from the descriptor
    :return: the container's args
    """

    cmd = settings['benchmark_code']

    if 'ml_args' in settings:
        cmd += ' ' + settings['ml_args']

    return cmd + ';'


def get_data_volumes(data_sources: List) -> Dict:
    # Data destination paths and the corresponding mounted vols
    destination_paths = set([s['path'] for s in data_sources])
    data_vols = {}

    for idx, dest in enumerate(destination_paths):
        name = 'p' + str(idx)
        puller_path = f'/data/{name}'
        data_vols[dest] = {'name': name,
                           'puller_path': puller_path}

    return data_vols


def get_pod_spec_volumes(settings: Dict):
    volumes = []

    if 'extended_shm' in settings:
        shm = k8s.client.V1Volume(name=SHARED_MEMORY_VOL,
                                  empty_dir=k8s.client.V1EmptyDirVolumeSource(medium="Memory")).to_dict()
        volumes.append(shm)

    if 'data_volumes' in settings:
        for _, vol in settings['data_volumes'].items():
            volumes.append(k8s.client.V1Volume(name=vol['name'],
                                               empty_dir=k8s.client.V1EmptyDirVolumeSource())
                           .to_dict())

    return remove_null_entries(volumes)


def get_container_volume_mounts(settings: Dict) -> List:
    vol_mounts = []

    if 'extended_shm' in settings:
        vol_mounts.append(k8s.client.V1VolumeMount(name=SHARED_MEMORY_VOL,
                                                   mount_path='/dev/shm')
                          .to_dict())

    for dest_path, vol in settings['data_volumes'].items():
        vol_mounts.append(k8s.client.V1VolumeMount(name=vol['name'],
                                                   mount_path=dest_path)
                          .to_dict())

    return remove_null_entries(vol_mounts)


def get_puller_volume_mounts(settings: Dict) -> List:
    vol_mounts = []

    for _, vol in settings['data_volumes'].items():
        vol_mounts.append(k8s.client.V1VolumeMount(name=vol['name'],
                                                   mount_path=vol['puller_path'])
                          .to_dict())

    return vol_mounts


def get_data_puller(settings: Dict):
    """
    Extracts the args for the data puller container and formats them.
    :param settings: dict with input parameters
    :return: dict with the puller object
    """
    processed_sources = []
    try:
        for source in settings['data_sources']:
            uri_components = process_uri(source['uri'])
            processed_sources.append({**source, **uri_components})
    except KeyError as e:
        raise KeyError('Required field is missing in the descriptor file.'
                       ' Each data source must have a download uri and a destination path.') from e
    except ValueError as e:
        raise ValueError('Incorrect download URI.') from e

    # TODO: Assuming only S3 sources here, will need modifications
    # Placeholder until the data fetcher is ready
    # ------------------------------------------
    unique_buckets = set([s['bucket'] for s in processed_sources])

    if len(unique_buckets) != 1:
        raise ValueError('Too many different S3 buckets to pull from (only one is allowed at the moment)')

    bucket = unique_buckets.pop()

    s3_objects = []
    for s in processed_sources:
        s3_objects.append(s['object'] + ',' +
                          MOUNT_CHMOD + ',' +
                          settings['data_volumes'][s['path']]['name'])

    puller_args = [S3_REGION, bucket, ':'.join(s3_objects)]
    # ------------------------------------------

    vol_mounts = get_puller_volume_mounts(settings)
    puller = k8s.client.V1Container(name='data-puller',
                                    image=PULLER_IMAGE,
                                    args=puller_args,
                                    volume_mounts=vol_mounts).to_dict()
    return remove_null_entries(puller)


def process_uri(uri):
    """
    Handles a data URI to extract the relevant information.
    :param uri: str starting with the source, such as s3://bucket/object-name
    :return: dict with the relevant information
    """
    origin, path = uri.split('://')
    if origin not in VALID_DATA_SOURCES:
        raise ValueError(f'Data source uri must start with one of the following:'
                         f' {a+":// " for a in VALID_DATA_SOURCES}')
    if origin == 's3':
        bucket = path.split('/')[0]
        s3_object = '/'.join(path.split('/')[1:])
        return {'source': 's3', 'bucket': bucket, 'object': s3_object}

    # TODO: Add data sources other than S3
    else:
        print(f'{origin} not supported as a data source yet')


def replace_templated_fields(d: Dict, templates: Dict[str, Dict]):
    """
    Iterates through the dict passed as parameter and replaces all templated fields with
    the corresponding values.
    :param d: dictionary containing values which need replacement
    :param templates: dict[str, dict] which holds the replacement values
    """
    if hasattr(d, 'items'):
        for k, v in d.copy().items():
            if is_templated_field(v):
                field_name = v[1:-1]  # Remove < >
                d[k] = templates[field_name]
            if isinstance(v, dict):
                replace_templated_fields(v, templates)
            elif isinstance(v, list):
                for elem in v:
                    replace_templated_fields(elem, templates)


def is_templated_field(val) -> bool:
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


if __name__ == '__main__':
    main()
