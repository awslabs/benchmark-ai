import toml
import argparse
import os
import uuid
import re


_REGEX_JOB_ID = '[^a-z0-9](^[-a-z0-9]*[a-z0-9])?'
_K8S_MAX_NAME_LENGTH = 63


def main():
    parser = argparse.ArgumentParser(description='Reads the descriptor file, creates the corresponding job config'
                                                 'yaml file and applies it to run a job.')
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

    if 'args' in descriptor['ml'].keys():
        settings['ml_args'] = descriptor['ml']['args']

    return settings


def fill_template(settings: dict, template: str):
    """
    Fill in the job config file
    :param settings: dict with the parsed input from the descriptor file
    :param template: dict with the input from the job config template
    :return: dict with job config
    """
    job_id = get_job_id(settings)
    settings['job_id'] = job_id
    settings['container_name'] = job_id
    settings['container_args'] = get_container_args(settings)

    return template.format(**settings)


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

    cmd = settings['benchmark_code'] \

    if 'ml_args' in settings.keys():
        cmd += ' ' + settings['ml_args']

    if 'download_cmd' in settings.keys():
        cmd = [settings['download_cmd'], cmd]

    if isinstance(cmd, str):
        return cmd + ';'
    else:
        return '; '.join(cmd).strip() + ';'


if __name__ == '__main__':
    main()
