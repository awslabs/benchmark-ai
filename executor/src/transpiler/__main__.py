import os
import toml

from argparse import ArgumentParser
from executor.args import create_executor_config
from transpiler.bai_knowledge import create_job_yaml_spec


def main(argv=None):
    # This method is only called when using the transpiler as a module of its own, which
    # is getting deprecated very soon
    transpiler_config = create_executor_config(argv)
    input = get_input_args(argv)
    descriptor_data = toml.load(input.descriptor)

    # TODO: Pass this as an argument
    fetched_data_sources = descriptor_data.get('data', {}).get('sources', [])

    yaml_string, _ = create_job_yaml_spec(descriptor_data,
                                          transpiler_config,
                                          fetched_data_sources)

    if input.filename:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, input.filename), 'w') as f:
            f.write(yaml_string)
    else:
        print(yaml_string)


def get_input_args(argv):
    parser = ArgumentParser()

    parser.add_argument('--descriptor',
                        help='Relative path to descriptor file',
                        required=True)

    parser.add_argument('-f', '--filename',
                        help='Output to file. If not specified, output to stdout',
                        default=None)

    parsed_args, _ = parser.parse_known_args(argv)
    return parsed_args


if __name__ == '__main__':
    main()
