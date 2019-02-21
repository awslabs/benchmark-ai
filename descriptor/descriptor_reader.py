import toml
import yaml
import argparse
import sys
import os
import uuid


def main():
    parser = argparse.ArgumentParser(description='Reads the descriptor file, creates the corresponding pod.yaml '
                                                 'config and applies it to run a pod.')
    parser.add_argument('file', help='Relative path to descriptor file')
    parser.add_argument('--pod_config_path', help='Relative path to pod config template file',
                        default='pod_config_template.yml')

    args = parser.parse_args()

    workdir = os.path.dirname(os.path.abspath(__file__))
    descriptor = toml.load(os.path.join(workdir, args.file))
    pod_config_path = os.path.join(workdir, args.pod_config_path)
    with open(pod_config_path, 'r') as stream:
        pod_config = yaml.safe_load(stream)

    # Fill in the pod config file
    # Extract args from [ml.params] subsection and prepend benchmark_code path
    container_args = [descriptor['ml']['benchmark_code']] + \
                     [f'{k}={v}' for k, v in descriptor['ml']['params'].items()]

    container = {'name': uuid.uuid4().hex,
                 'image': descriptor['env']['docker_image'],
                 'args': container_args}

    pod_config["metadata"]["name"] = "container1"
    pod_config["spec"]["containers"] = [container]

    with open(os.path.join(workdir, 'pod.yml'), 'w') as outfile:
        yaml.dump(pod_config, outfile, default_flow_style=False)


if __name__ == '__main__':
    main()
