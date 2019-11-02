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
from dataclasses import dataclass
from typing import List

from bai_watcher.status_inferrers.status import BenchmarkJobStatus
from configargparse import ArgParser

from bai_job_status_trigger import APP_NAME


@dataclass
class JobStatusTriggerConfig:
    job_namespace: str
    job_name: str
    trigger_statuses: List[BenchmarkJobStatus]
    job_not_found_grace_period_seconds: int
    command: str


def get_job_status_trigger_config(args) -> JobStatusTriggerConfig:
    parser = ArgParser(auto_env_var_prefix="", prog=APP_NAME)

    def benchmark_status_from_input(input: str) -> BenchmarkJobStatus:
        return BenchmarkJobStatus(input.strip(" \t,"))

    # required
    parser.add_argument("--job-name", type=str, env_var="JOB_NAME", required=True)
    parser.add_argument(
        "--trigger-statuses", type=benchmark_status_from_input, nargs="+", env_var="TRIGGER_STATUSES", required=True
    )
    parser.add_argument("--command", type=str, env_var="COMMAND", required=True)

    # optional
    parser.add_argument("--job-namespace", type=str, default="default", env_var="JOB_NAMESPACE", required=False)
    parser.add_argument(
        "--job-not-found-grace-period-seconds",
        type=int,
        default=30,
        env_var="JOB_NOT_FOUND_GRACE_PERIOD_SECONDS",
        required=False,
    )

    parsed_args, _ = parser.parse_known_args(args)

    return JobStatusTriggerConfig(
        job_namespace=parsed_args.job_namespace,
        job_name=parsed_args.job_name,
        trigger_statuses=parsed_args.trigger_statuses,
        job_not_found_grace_period_seconds=parsed_args.job_not_found_grace_period_seconds,
        command=parsed_args.command,
    )
