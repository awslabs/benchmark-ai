import os
import json
import configargparse

from transpiler.config import DescriptorConfig, BaiConfig


def get_args(argv):
    base_dir = os.path.abspath(os.path.dirname(__file__))

    parser = configargparse.ArgParser(default_config_files=[os.path.join(base_dir, 'config.yaml')],
                                      config_file_parser_class=configargparse.YAMLConfigFileParser,
                                      description='Reads the descriptor file and creates the '
                                                  'corresponding job config yaml file.')

    parser.add('-c', '--my-config', required=False, is_config_file=True,
               help='Config file path')

    parser.add_argument('descriptor',
                        help='Relative path to descriptor file')

    parser.add_argument('-f', '--filename',
                        help='Output to file. If not specified, output to stdout',
                        default=None)

    parser.add_argument('--availability-zones', nargs='+',
                        help='All the availability zones which the benchmark can run',
                        required=True)

    parser.add('--shared_memory_vol',
               help='Name of the shared memory volume for Kubernetes jobs',
               default='dshm')

    parser.add('--puller_mount_chmod',
               help='Permissions to set for files downloaded by the data puller')

    parser.add('--puller_s3_region',
               help='Region for the data pullers S3 bucket')

    parser.add('--puller_docker_image',
               help='Docker image used by the data puller')

    parser.add('--valid_strategies', type=json.loads,
               help='List of valid strategies such as single_node or horovod')

    return parser.parse_args(argv)


def create_descriptor_config(args):
    return DescriptorConfig(valid_strategies=args.valid_strategies)


def create_bai_config(args):
    return BaiConfig(shared_memory_vol=args.shared_memory_vol,
                     puller_mount_chmod=args.puller_mount_chmod,
                     puller_s3_region=args.puller_s3_region,
                     puller_docker_image=args.puller_docker_image)
