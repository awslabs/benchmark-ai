import toml
import argparse
import os
import uuid

from typing import Dict


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
            outfile.write(job_config)
    else:
        print(job_config)


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
            'benchmark_code': descriptor['ml']['benchmark_code'],
        }
    except KeyError as e:
        raise KeyError('Required field is missing in the descriptor file') from e

    if 'data' in descriptor['ml']:
        settings['dataset'] = descriptor['ml']['data']['dataset']
        if 'download_script' in descriptor['ml']['data']:
            settings['download_cmd'] = descriptor['ml']['data']['download_script']

    if 'args' in descriptor['ml']:
        settings['ml_args'] = descriptor['ml']['args']

    settings['privileged'] = False if 'privileged' not in settings['env'] else settings['env']['privileged']

    return settings


def fill_template(settings: Dict[str, str], template: str) -> str:
    """
    Fill in the job config file
    :param settings: dict with the parsed input from the descriptor file
    :param template: dict with the input from the job config template
    :return: job config string
    """
    # TODO: Verify there are K8s labels to store info such as dataset, docker_image, instance_type...
    job_id = uuid.uuid4().hex
    settings['job_id'] = job_id
    settings['container_name'] = job_id
    settings['container_args'] = get_container_args(settings)

    return template.format(**settings)


def get_container_args(settings: Dict[str, str]) -> str:
    """
    Extracts the args for the container and formats them.
    :param settings: dict containing the parsed input from the descriptor
    :return: the container's args
    """

    cmd = settings['benchmark_code']

    if 'ml_args' in settings:
        cmd += ' ' + settings['ml_args']

    if 'download_cmd' in settings:
        cmd = settings['download_cmd'] + '; ' + cmd

    return cmd + ';'


if __name__ == '__main__':
    main()
