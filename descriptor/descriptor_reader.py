import toml
import yaml
import argparse
import os
import sys
import uuid
import re
from collections import OrderedDict

_REGEX_JOB_ID = '[^a-z0-9](^[-a-z0-9]*[a-z0-9])?'
_K8S_MAX_NAME_LENGTH = 63


def main():
    parser = argparse.ArgumentParser(description='Reads the descriptor file, creates the corresponding job config'
                                                 'yaml file and applies it to run a job.')
    parser.add_argument('descriptor',
                        help='Relative path to descriptor file')

    parser.add_argument('--template',
                        help='Relative path to pod config template file',
                        default='job_config_template.yaml')

    parser.add_argument('-f', metavar='outfile', nargs='?',
                        help='Output to file. If not specified, output to stdout',
                        default=None,
                        const='job_config.yaml')

    setup_yaml()

    args = parser.parse_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, args.template), 'r') as stream:
        template = ordered_load(stream, yaml.SafeLoader)

    settings = read_descriptor(os.path.join(current_dir, args.descriptor))
    job_config = fill_template(settings, template)

    if args.f:
        with open(os.path.join(current_dir, args.f), 'w') as outfile:
            yaml.dump(job_config, outfile, default_flow_style=False)
    else:
        yaml.dump(job_config, sys.stdout, default_flow_style=False)


def read_descriptor(descriptor_path):
    """
    Reads the values from the descriptor file into a dictionary
    :param descriptor_path: path to the descriptor file
    :return:
    """
    descriptor = toml.load(descriptor_path)

    settings = {
        'instance_type': descriptor['hardware']['instance_type'],
        'docker_image': descriptor['env']['docker_image'],
        'benchmark_code': descriptor['ml']['benchmark_code'],
    }

    if 'data' in descriptor['ml'].keys():
        settings['dataset'] = descriptor['ml']['data']['dataset']
        if 'download_script' in descriptor['ml']['data'].keys():
            settings['download_cmd'] = descriptor['ml']['data']['download_script']

    if 'params' in descriptor['ml'].keys():
        settings['ml.params'] = [f'--{k}={v}' for k, v in descriptor['ml']['params'].items()]

    return settings


def fill_template(settings: dict, template: dict):
    """
    Fill in the job config file
    :param settings: dict with the parsed input from the descriptor file
    :param template: dict with the input from the job config template
    :return: dict with job config
    """
    spec = template['spec']['template']['spec']

    job_id = get_job_id(settings)
    container_args = get_container_args(settings)

    container = OrderedDict({'name': job_id,
                             'image': settings['docker_image'],
                             'command':  spec['containers'][0]['command'],
                             'args': container_args})

    spec['containers'] = [container]
    spec['nodeSelector'] = {'beta.kubernetes.io/instance-type': settings['instance_type']}

    template['metadata'] = {'name': job_id}
    template['spec']['template']['spec'] = spec

    return template


def get_job_id(settings):
    """
    Creates a unique identifier for this job, based on the descriptor plus a random part
    :return:
    """
    id_components = [settings['docker_image'], settings['instance_type']]
    if 'dataset' in settings.keys():
        id_components += settings['dataset']

    # TODO: replace _ with -
    descriptor_id = '_'.join(id_components)

    job_id = f'{descriptor_id}{uuid.uuid4().hex}'
    job_id = re.sub(_REGEX_JOB_ID, '', job_id)

    if len(job_id) > _K8S_MAX_NAME_LENGTH:
        job_id = job_id[:_K8S_MAX_NAME_LENGTH]

    return job_id


def get_container_args(settings: dict):
    """
    Extracts the args for the container and formats them.
    :param settings: dict containing the parsed input from the descriptor
    :return: dict representing the container's args
    """

    cmd = ' '.join([settings['benchmark_code']] + settings['ml.params'])

    if 'download_cmd' in settings.keys():
        cmd = [settings['download_cmd'], cmd]

    if isinstance(cmd, str):
        return cmd + ';'
    else:
        return ['; '.join(cmd).strip() + ';']


def setup_yaml():
    """
    Workaround to allow PyYaml to represent OrderedDicts
    https://stackoverflow.com/a/8661021
    """
    represent_dict_order = lambda self, data:  self.represent_mapping('tag:yaml.org,2002:map', data.items())
    yaml.add_representer(OrderedDict, represent_dict_order)


def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    """
    Workaround to have PyYaml preserve order when loading files
    """
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


if __name__ == '__main__':
    main()
