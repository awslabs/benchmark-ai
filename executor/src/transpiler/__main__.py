import os
import toml

from executor.args import get_args, create_transpiler_config
from transpiler.bai_knowledge import create_job_yaml_spec


def main(argv=None):
    transpiler_config = create_transpiler_config(argv)
    descriptor_data = toml.load(transpiler_config.descriptor_path)

    # TODO: Pass this as an argument
    fetched_data_sources = descriptor_data.get('data', {}).get('sources', [])

    yaml_string, _ = create_job_yaml_spec(descriptor_data,
                                          transpiler_config,
                                          fetched_data_sources)

    if transpiler_config.filename:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, transpiler_config.filename), 'w') as f:
            f.write(yaml_string)
    else:
        print(yaml_string)


if __name__ == '__main__':
    main()
