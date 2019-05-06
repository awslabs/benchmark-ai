import os
import json
import configargparse

from transpiler.config import DescriptorConfig, BaiConfig, EnvironmentInfo
from executor.config import ExecutorConfig


def get_args(argv):
    def list_str(values):
        return values.split(',')

    base_dir = os.path.abspath(os.path.dirname(__file__))
    config_file = os.path.join(base_dir, "default_config.yaml")

    parser = configargparse.ArgParser(
        default_config_files=[config_file],
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        description="Reads the descriptor file and creates the " "corresponding job config yaml file.",
    )

    parser.add("-c", "--my-config", required=False, is_config_file=True, help="Config file path")

    parser.add(
        "--availability-zones",
        type=list_str,
        env_var="AVAILABILITY_ZONES",
        help="All the availability zones which the benchmark can run, as a comma-separated list",
    )

    parser.add(
        "--transpiler-puller-mount-chmod",
        env_var="TRANSPILER_PULLER_MOUNT_CHMOD",
        dest="puller_mount_chmod",
        help="Permissions to set for files downloaded by the data puller",
    )

    parser.add(
        "--transpiler-puller-s3-region",
        env_var="TRANSPILER_PULLER_S3_REGION",
        dest="puller_s3_region",
        help="Region for the data pullers S3 bucket",
    )

    parser.add(
        "--transpiler-puller-docker-image",
        env_var="TRANSPILER_PULLER_DOCKER_IMAGE",
        dest="puller_docker_image",
        help="Docker image used by the data puller",
    )

    parser.add(
        "--transpiler-valid-strategies",
        type=json.loads,
        env_var="TRANSPILER_VALID_STRATEGIES",
        dest="valid_strategies",
        help="List of valid strategies such as single_node or horovod",
    )

    parser.add("--kubeconfig", env_var="KUBECONFIG", help="Kubeconfig option for kubectl")

    parsed_args, _ = parser.parse_known_args(argv)
    return parsed_args


def create_descriptor_config(args):
    return DescriptorConfig(valid_strategies=args.valid_strategies)


def create_bai_config(args):
    return BaiConfig(
        puller_mount_chmod=args.puller_mount_chmod,
        puller_s3_region=args.puller_s3_region,
        puller_docker_image=args.puller_docker_image,
    )


def create_executor_config(argv):
    args = get_args(argv)
    environment_info = EnvironmentInfo(availability_zones=args.availability_zones)
    return ExecutorConfig(
        kubeconfig=args.kubeconfig,
        descriptor_config=create_descriptor_config(args),
        bai_config=create_bai_config(args),
        environment_info=environment_info,
    )
