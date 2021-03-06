#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import json
import os
import configargparse
from bai_kafka_utils.executors.descriptor import DescriptorConfig

from transpiler.config import BaiConfig, EnvironmentInfo

from executor.config import ExecutorConfig


def get_args(argv, env=None):
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
        "--availability-zones",
        type=json.loads,
        env_var="AVAILABILITY_ZONES",
        help="All the availability zones which the benchmark can run, as json mapping zone-ids to zone-names",
        required=True,
    )

    parser.add(
        "--transpiler-puller-mount-chmod",
        env_var="TRANSPILER_PULLER_MOUNT_CHMOD",
        dest="puller_mount_chmod",
        help="Permissions to set for files downloaded by the data puller",
    )

    parser.add(
        "--transpiler-puller-docker-image",
        env_var="TRANSPILER_PULLER_DOCKER_IMAGE",
        dest="puller_docker_image",
        help="Docker image used by the data puller",
    )

    parser.add(
        "--transpiler-metrics-pusher-docker-image",
        env_var="TRANSPILER_METRICS_PUSHER_DOCKER_IMAGE",
        dest="metrics_pusher_docker_image",
        help="Docker image used by the metrics pusher",
    )

    parser.add(
        "--transpiler-metrics-extractor-docker-image",
        env_var="TRANSPILER_METRICS_EXTRACTOR_DOCKER_IMAGE",
        dest="metrics_extractor_docker_image",
        help="Docker image used by the metrics extractor",
    )

    parser.add(
        "--transpiler-job-status-trigger-docker-image",
        env_var="TRANSPILER_JOB_STATUS_TRIGGER_DOCKER_IMAGE",
        dest="job_status_trigger_docker_image",
        help="Docker image used by inference server benchmark to sync client and server",
    )

    parser.add(
        "--transpiler-cron-job-docker-image",
        env_var="TRANSPILER_CRON_JOB_DOCKER_IMAGE",
        dest="cron_job_docker_image",
        help="Docker image used by k8s cron job to kick off periodic benchmarks",
    )

    parser.add(
        "--transpiler-valid-strategies",
        type=list_str,
        env_var="TRANSPILER_VALID_STRATEGIES",
        dest="valid_strategies",
        help="List of valid strategies such as single_node or horovod",
    )

    parser.add(
        "--transpiler-valid-frameworks",
        type=list_str,
        env_var="TRANSPILER_VALID_FRAMEWORKS",
        dest="valid_frameworks",
        help="List of valid frameworks such as tensorflow or mxnet",
    )

    parser.add(
        "--valid-execution-engines",
        type=list_str,
        env_var="VALID_EXECUTION_ENGINES",
        dest="valid_execution_engines",
        help="List of valid execution engines, such as kubernetes or sagemaker",
        default=[],
    )

    parser.add("--suppress-job-affinity", env_var="SUPPRESS_JOB_AFFINITY", action="store_true")

    parser.add("--kubectl", env_var="KUBECTL", help="Path to kubectl in the deployment pod")

    parsed_args, _ = parser.parse_known_args(argv, env_vars=env)
    return parsed_args


def create_descriptor_config(args):
    return DescriptorConfig(valid_strategies=args.valid_strategies, valid_frameworks=args.valid_frameworks)


def create_bai_config(args):
    return BaiConfig(
        puller_mount_chmod=args.puller_mount_chmod,
        puller_docker_image=args.puller_docker_image,
        metrics_pusher_docker_image=args.metrics_pusher_docker_image,
        metrics_extractor_docker_image=args.metrics_extractor_docker_image,
        cron_job_docker_image=args.cron_job_docker_image,
        job_status_trigger_docker_image=args.job_status_trigger_docker_image,
        suppress_job_affinity=args.suppress_job_affinity,
    )


def create_executor_config(argv, env=os.environ):
    args = get_args(argv, env)
    environment_info = EnvironmentInfo(args.availability_zones)
    return ExecutorConfig(
        kubectl=args.kubectl,
        descriptor_config=create_descriptor_config(args),
        bai_config=create_bai_config(args),
        environment_info=environment_info,
        valid_execution_engines=args.valid_execution_engines,
    )
