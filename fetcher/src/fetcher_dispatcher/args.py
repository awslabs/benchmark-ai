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
from dataclasses import dataclass, field

from configargparse import ArgParser
from typing import Optional, Dict

from fetcher_dispatcher import SERVICE_NAME

MIN_VOLUME_SIZE_MB = 64 * 1024  # 64 gb


@dataclass
class FetcherVolumeConfig:
    min_size: int = 0  # In MB
    storage_class: Optional[str] = None


@dataclass
class FetcherJobConfig:
    image: str
    namespace: str
    pull_policy: Optional[str] = None
    restart_policy: Optional[str] = None
    ttl: Optional[int] = None
    node_selector: Dict[str, str] = field(default_factory=dict)
    volume: FetcherVolumeConfig = FetcherVolumeConfig()


@dataclass
class FetcherServiceConfig:
    zookeeper_ensemble_hosts: str
    s3_download_bucket: str
    fetcher_job: FetcherJobConfig
    kubeconfig: Optional[str] = None


# We ignore unrecognized objects at the moment
def get_fetcher_service_config(args) -> FetcherServiceConfig:
    parser = ArgParser(auto_env_var_prefix="", prog=SERVICE_NAME)

    parser.add_argument("--zookeeper-ensemble-hosts", env_var="ZOOKEEPER_ENSEMBLE_HOSTS", default="localhost:2181")

    parser.add_argument("--s3-download-bucket", env_var="S3_DOWNLOAD_BUCKET", required=True)

    parser.add_argument("--kubeconfig", env_var="KUBECONFIG")

    parser.add_argument("--fetcher-job-image", env_var="FETCHER_JOB_IMAGE", required=True)

    parser.add_argument("--fetcher-job-ttl", env_var="FETCHER_JOB_TTL", type=int, required=False)

    parser.add_argument("--fetcher-job-node-selector", env_var="FETCHER_JOB_NODE_SELECTOR", type=json.loads, default={})

    parser.add_argument(
        "--fetcher-job-pull-policy",
        env_var="FETCHER_JOB_PULL_POLICY",
        required=False,
        # Default is complicated - Always if not tag, IfNotPresent - otherwise
        choices=["Always", "Never", "IfNotPresent"],
    )

    parser.add_argument(
        "--fetcher-job-restart-policy",
        env_var="FETCHER_JOB_RESTART_POLICY",
        required=False,
        choices=["Never", "OnFailure"],
        default="OnFailure",
    )

    parser.add_argument("--fetcher-job-namespace", env_var="FETCHER_JOB_NAMESPACE", required=False, default="default")
    parser.add_argument(
        "--fetcher-job-min-volume-size",
        env_var="FETCHER_JOB_MIN_VOLUME_SIZE",
        required=False,
        type=int,
        default=MIN_VOLUME_SIZE_MB,
    )
    parser.add_argument(
        "--fetcher-job-volume-storage-class", env_var="FETCHER_JOB_VOLUME_STORAGE_CLASS", required=False
    )

    parsed_args, _ = parser.parse_known_args(args, env_vars=os.environ)
    return FetcherServiceConfig(
        zookeeper_ensemble_hosts=parsed_args.zookeeper_ensemble_hosts,
        s3_download_bucket=parsed_args.s3_download_bucket,
        kubeconfig=parsed_args.kubeconfig,
        fetcher_job=FetcherJobConfig(
            namespace=parsed_args.fetcher_job_namespace,
            image=parsed_args.fetcher_job_image,
            node_selector=parsed_args.fetcher_job_node_selector,
            pull_policy=parsed_args.fetcher_job_pull_policy,
            ttl=parsed_args.fetcher_job_ttl,
            restart_policy=parsed_args.fetcher_job_restart_policy,
            volume=FetcherVolumeConfig(
                storage_class=parsed_args.fetcher_job_volume_storage_class,
                min_size=parsed_args.fetcher_job_min_volume_size,
            ),
        ),
    )
