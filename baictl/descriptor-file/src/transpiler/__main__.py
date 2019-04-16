import os
import toml

from transpiler.args import get_args
from transpiler.descriptor import Descriptor, DescriptorSettings
from transpiler.bai_knowledge import create_bai_config, EnvironmentInfo
from typing import Dict


def main(argv=None):
    args = get_args(argv)

    descriptor_data = toml.load(args.descriptor)
    environment_info = EnvironmentInfo(
        availability_zones=args.availability_zones
    )

    yaml_string = create_yaml_spec(descriptor_data, args, environment_info)

    if args.filename:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, args.filename), 'w') as f:
            f.write(yaml_string)
    else:
        print(yaml_string)


def create_yaml_spec(descriptor_contents: Dict, args, environment_info: EnvironmentInfo):
    """
    Creates the YAML spec file corresponding to a descriptor passed as parameter
    :param descriptor_contents: dict containing the parsed descriptor
    :param environment_info: contains BAI information, such as availability zones, etc
    :return: The yaml string for the given descriptor
    """
    descriptor_config = DescriptorSettings(**args)

    descriptor = Descriptor(descriptor_contents, descriptor_config)
    bai_config = create_bai_config(descriptor, args, environment_info=environment_info)
    return bai_config.dump_yaml_string()


if __name__ == '__main__':
    main()
