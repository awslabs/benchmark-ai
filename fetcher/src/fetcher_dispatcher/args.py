import json
from dataclasses import dataclass, field

from configargparse import ArgParser
from typing import Optional, Dict

from fetcher_dispatcher import SERVICE_NAME


@dataclass
class FetcherServiceConfig:
    zookeeper_ensemble_hosts: str
    s3_data_set_bucket: str
    fetcher_job_image: str
    fetcher_job_node_selector: Dict[str, str] = field(default_factory=dict)
    kubeconfig: Optional[str] = None


# We ignore unrecognized objects at the moment
def get_fetcher_service_config(args) -> FetcherServiceConfig:
    parser = ArgParser(auto_env_var_prefix="", prog=SERVICE_NAME)

    parser.add_argument(
        "--zookeeper-ensemble-hosts",
        env_var="ZOOKEEPER_ENSEMBLE_HOSTS",
        default="localhost:2181",
    )

    parser.add_argument(
        "--s3-data-set-bucket", env_var="S3_DATASET_BUCKET", required=True
    )

    parser.add_argument("--kubeconfig", env_var="KUBECONFIG")

    parser.add_argument(
        "--fetcher-job-image", env_var="FETCHER_JOB_IMAGE", required=True
    )

    parser.add_argument(
        "--fetcher-job-node-selector",
        env_var="FETCHER_NODE_SELECTOR",
        type=json.loads,
        default={},
    )

    parsed_args, _ = parser.parse_known_args(args)
    return FetcherServiceConfig(
        zookeeper_ensemble_hosts=parsed_args.zookeeper_ensemble_hosts,
        s3_data_set_bucket=parsed_args.s3_data_set_bucket,
        kubeconfig=parsed_args.kubeconfig,
        fetcher_job_image=parsed_args.fetcher_job_image,
        fetcher_job_node_selector=parsed_args.fetcher_job_node_selector,
    )
