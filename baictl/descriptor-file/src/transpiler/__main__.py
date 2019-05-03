import os
import toml

from transpiler.args import get_args, create_bai_config, create_descriptor_config
from transpiler.bai_knowledge import EnvironmentInfo, create_yaml_spec
from bai_kafka_utils.events import DataSet


def main(argv=None):
    args = get_args(argv)
    descriptor_config = create_descriptor_config(args)
    bai_config = create_bai_config(args)

    descriptor_data = toml.load(args.descriptor)
    environment_info = EnvironmentInfo(
        availability_zones=args.availability_zones
    )

    # TODO: Pass this as an argument
    fetched_data_sources = descriptor_data.get('data', {}).get('sources', [])
    fetched_data_sources = [DataSet(src=source['src'], dst=source['src']) for source in fetched_data_sources]

    yaml_string = create_yaml_spec(descriptor_data,
                                   descriptor_config,
                                   bai_config,
                                   fetched_data_sources,
                                   environment_info=environment_info)

    if args.filename:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, args.filename), 'w') as f:
            f.write(yaml_string)
    else:
        print(yaml_string)


if __name__ == '__main__':
    main()
