import toml
import yaml
import argparse
import os
import sys
import uuid
from collections import OrderedDict


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

    workdir = os.path.dirname(os.path.abspath(__file__))
    descriptor = toml.load(os.path.join(workdir, args.descriptor))
    job_config_path = os.path.join(workdir, args.template)
    with open(job_config_path, 'r') as stream:
        job_config = ordered_load(stream, yaml.SafeLoader)

    # Fill in the job config file
    spec = job_config['spec']['template']['spec']

    instance_type = descriptor['hardware']['instance_type']
    docker_image = descriptor['env']['docker_image']
    dataset = descriptor['ml']['data']['dataset']

    # Unique identifier for this job, based on the descriptor plus a random part
    descriptor_id = '_'.join([docker_image, dataset, instance_type])
    job_id = f'{descriptor_id}-{uuid.uuid4().hex}'

    # Extract args from [ml.params] subsection and prepend benchmark_code path
    container_args = spec['containers'][0]['args'][0].split(';')
    download_cmd = descriptor['ml']['data']['download_script'] + ' ' + dataset
    benchmark_cmd = ' '.join([descriptor['ml']['benchmark_code']] +
                             [f'{k}={v}' for k, v in descriptor['ml']['params'].items()])
    container_args[1] = download_cmd
    container_args[3] = benchmark_cmd
    container_args = '; '.join(container_args).strip()

    container = OrderedDict({'name': job_id,
                             'image': docker_image,
                             'command': spec['containers'][0]['command'],
                             'args': container_args})

    spec['containers'] = [container]
    spec['nodeSelector'] = {'beta.kubernetes.io/instance-type': instance_type}

    job_config['metadata'] = {'name': job_id}
    job_config['spec']['template']['spec'] = spec

    if args.f:
        with open(os.path.join(workdir, args.f), 'w') as outfile:
            yaml.dump(job_config, outfile, default_flow_style=False)
    else:
        yaml.dump(job_config, sys.stdout, default_flow_style=False)


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
