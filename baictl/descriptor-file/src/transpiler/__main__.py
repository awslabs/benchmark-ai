import os

from transpiler.args import get_args
from transpiler.descriptor import Descriptor, DescriptorSettings
from transpiler.bai_knowledge import create_bai_config, EnvironmentInfo


def main(argv=None):
    args = get_args(argv)

    descriptor_config = DescriptorSettings(**args)
    descriptor = Descriptor.from_toml_file(args.descriptor, descriptor_config)

    environment_info = EnvironmentInfo(
        availability_zones=args.availability_zones
    )
    bai_config = create_bai_config(descriptor, args, environment_info=environment_info)
    yaml_string = bai_config.dump_yaml_string()

    if args.filename:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, args.filename), 'w') as f:
            f.write(yaml_string)
    else:
        print(yaml_string)


if __name__ == '__main__':
    main()
