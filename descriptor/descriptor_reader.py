import toml
import yaml
import argparse
import os
import uuid
from collections import OrderedDict


def main():
    parser = argparse.ArgumentParser(description='Reads the descriptor file, creates the corresponding job config'
                                                 'yaml file and applies it to run a job.')
    parser.add_argument('file',
                        help='Relative path to descriptor file')

    parser.add_argument('--template',
                        help='Relative path to pod config template file',
                        default='job_config_template.yaml')

    parser.add_argument('--output',
                        help='Output file name',
                        default='job_config.yaml')

    setup_yaml()

    args = parser.parse_args()

    workdir = os.path.dirname(os.path.abspath(__file__))
    descriptor = toml.load(os.path.join(workdir, args.file))
    pod_config_path = os.path.join(workdir, args.template)
    with open(pod_config_path, 'r') as stream:
        pod_config = ordered_load(stream, yaml.SafeLoader)

    # Fill in the job config file
    # Extract args from [ml.params] subsection and prepend benchmark_code path
    container_args = [descriptor['ml']['benchmark_code']] + \
                     [f'{k}={v}' for k, v in descriptor['ml']['params'].items()]

    container = OrderedDict({'name': uuid.uuid4().hex,
                             'image': descriptor['env']['docker_image'],
                             'args': container_args})

    spec = pod_config['spec']['template']['spec']
    spec['containers'] = [container]
    spec['nodeSelector'] = {'beta.kubernetes.io/instance-type': descriptor['hardware']['instance_type']}

    pod_config['metadata'] = {'name': f'mxnet-{uuid.uuid4().hex}'}
    pod_config['spec']['template']['spec'] = spec

    with open(os.path.join(workdir, args.output), 'w') as outfile:
        yaml.dump(pod_config, outfile, default_flow_style=False)


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
