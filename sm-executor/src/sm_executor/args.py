import os
from dataclasses import dataclass, field

import configargparse
from bai_kafka_utils.executors.descriptor import DescriptorConfig
from typing import List

from sm_executor import SERVICE_NAME


@dataclass
class SageMakerExecutorConfig:
    s3_output_bucket: str
    sm_role: str
    tmp_sources_dir: str
    s3_nodata: str
    descriptor_config: DescriptorConfig
    security_group_ids: List[str] = None
    subnets: List[str] = None
    valid_execution_engines: List[str] = field(default_factory=list)


def get_args(argv, env=None):
    def list_str(values):
        return values.split(",")

    base_dir = os.path.abspath(os.path.dirname(__file__))
    config_file = os.path.join(base_dir, "default_config.yaml")

    parser = configargparse.ArgParser(auto_env_var_prefix="", prog=SERVICE_NAME, default_config_files=[config_file])

    parser.add("--sagemaker-output-bucket", required=True)
    parser.add("--sagemaker-role", required=True)
    parser.add("--tmp-sources-dir", required=False)
    parser.add("--sagemaker-nodataset", required=True)
    parser.add("--sagemaker-subnets", type=list_str, required=False)
    parser.add("--sagemaker-security-group-ids", type=list_str, required=False)
    parser.add("--valid-execution-engines", type=list_str, default=[])
    parser.add("--transpiler-valid-strategies", type=list_str, default=[])
    parser.add("--transpiler-valid-frameworks", type=list_str, default=[])

    parsed_args, _ = parser.parse_known_args(argv, env_vars=env)
    return parsed_args


def create_descriptor_config(args):
    return DescriptorConfig(
        valid_strategies=args.transpiler_valid_strategies, valid_frameworks=args.transpiler_valid_frameworks
    )


def create_executor_config(argv, env=os.environ):
    args = get_args(argv, env)
    return SageMakerExecutorConfig(
        valid_execution_engines=args.valid_execution_engines,
        sm_role=args.sagemaker_role,
        tmp_sources_dir=args.tmp_sources_dir,
        s3_nodata=args.sagemaker_nodataset,
        s3_output_bucket=args.sagemaker_output_bucket,
        security_group_ids=args.sagemaker_security_group_ids,
        subnets=args.sagemaker_subnets,
        descriptor_config=create_descriptor_config(args),
    )
