import os
import toml

from transpiler.args import get_args
from transpiler.descriptor import Descriptor
from transpiler.bai_knowledge import create_bai_k8s_builder, EnvironmentInfo
from transpiler.config import DescriptorConfig, BaiConfig
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


def create_yaml_spec(descriptor_contents: Dict,
                     descriptor_config: DescriptorConfig,
                     bai_config: BaiConfig,
                     environment_info: EnvironmentInfo,
                     extra_bai_config_args=None):
    """
    Creates the YAML spec file corresponding to a descriptor passed as parameter
    :param descriptor_contents: dict containing the parsed descriptor
    :param descriptor_config: configuration for the descriptor
    :param bai_config: configuration for the BaiKubernetesObjectBuilder
    :param environment_info: contains BAI information, such as availability zones, etc
    :param extra_bai_config_args: An optional Dict which will be forwarded to the `BaiConfig` object created.
    :return: The yaml string for the given descriptor
    """
    descriptor = Descriptor(descriptor_contents, descriptor_config)
    bai_k8s_builder = create_bai_k8s_builder(descriptor,
                                             bai_config,
                                             environment_info=environment_info,
                                             extra_bai_config_args=extra_bai_config_args)
    return bai_k8s_builder.dump_yaml_string()


if __name__ == '__main__':
    main()
