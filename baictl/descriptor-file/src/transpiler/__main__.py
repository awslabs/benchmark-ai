import argparse
import configparser
import os

from transpiler.bai_knowledge import create_bai_config, EnvironmentInfo
from transpiler.descriptor import Descriptor, DescriptorSettings


def main():
    parser = argparse.ArgumentParser(description='Reads the descriptor file and creates the '
                                                 'corresponding job config yaml file.')

    parser.add_argument('descriptor',
                        help='Relative path to descriptor file')

    parser.add_argument('-f', '--filename', metavar='filename', nargs='?',
                        help='Output to file. If not specified, output to stdout',
                        default=None,
                        const='job_config.yaml')

    parser.add_argument('--availability-zones', nargs='+',
                        help='All the availability zones which the benchmark can run',
                        required=True)

    args = parser.parse_args()

    config = _read_config()
    descriptor_config = DescriptorSettings(**config.get('descriptor'))
    descriptor = Descriptor.from_toml_file(args.descriptor, descriptor_config)

    environment_info = EnvironmentInfo(
        availability_zones=args.availability_zones
    )
    bai_config = create_bai_config(descriptor, config, environment_info=environment_info)
    yaml_string = bai_config.dump_yaml_string()

    if args.filename:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, args.filename), 'w') as f:
            f.write(yaml_string)
    else:
        print(yaml_string)


def _read_config():
    config = configparser.ConfigParser()
    file_dir = os.path.dirname(os.path.abspath(__file__))
    config.read(os.path.join(file_dir, 'settings.ini'))
    return config


if __name__ == '__main__':
    main()
