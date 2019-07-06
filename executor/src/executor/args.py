import os
import configargparse

from transpiler.config import BaiConfig, EnvironmentInfo, AvailabilityZoneInfo
from transpiler.descriptor import DescriptorConfig
from executor.config import ExecutorConfig


def get_args(argv):
    def list_str(values):
        return values.split(",")

    base_dir = os.path.abspath(os.path.dirname(__file__))
    config_file = os.path.join(base_dir, "default_config.yaml")

    parser = configargparse.ArgParser(
        default_config_files=[config_file],
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        description="Reads the descriptor file and creates the " "corresponding job config yaml file.",
    )

    parser.add("-c", "--my-config", required=False, is_config_file=True, help="Config file path")

    parser.add(
        "--availability-zones-names",
        type=list_str,
        env_var="AVAILABILITY_ZONES_NAMES",
        help="All the availability zones which the benchmark can run, as a comma-separated list",
        required=True,
    )
    parser.add(
        "--availability-zones-ids",
        type=list_str,
        env_var="AVAILABILITY_ZONES_IDS",
        help="Zone Ids of the passed availability zones",
        required=True,
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
        type=list_str,
        env_var="TRANSPILER_VALID_STRATEGIES",
        dest="valid_strategies",
        help="List of valid strategies such as single_node or horovod",
    )

    parser.add("--kubectl", env_var="KUBECTL", help="Path to kubectl in the deployment pod")

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


def create_environment_info(args) -> EnvironmentInfo:
    availability_zones_names = args.availability_zones_names
    availability_zones_ids = args.availability_zones_ids

    zones = [
        AvailabilityZoneInfo(name, zone_id) for name, zone_id in zip(availability_zones_names, availability_zones_ids)
    ]
    return EnvironmentInfo(zones)


def create_executor_config(argv):
    args = get_args(argv)
    environment_info = create_environment_info(args)
    return ExecutorConfig(
        kubectl=args.kubectl,
        descriptor_config=create_descriptor_config(args),
        bai_config=create_bai_config(args),
        environment_info=environment_info,
    )
