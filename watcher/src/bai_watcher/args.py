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

from configargparse import ArgParser

from bai_watcher import SERVICE_NAME


@dataclass
class WatcherServiceConfig:
    grafana_endpoint: str
    grafana_results_url: str
    grafana_op_metrics_dashboard_uid: str
    kubernetes_namespace_of_running_jobs: str = "default"
    kubeconfig: str = None
    logging_level: str = "INFO"


def get_watcher_service_config(args) -> WatcherServiceConfig:
    parser = ArgParser(auto_env_var_prefix="", prog=SERVICE_NAME)

    parser.add_argument(
        "--kubernetes-namespace-of-running-jobs", default="default", env_var="KUBERNETES_NAMESPACE_OF_RUNNING_JOBS"
    )
    parser.add_argument("--kubeconfig", env_var="KUBECONFIG")
    parser.add_argument("--service-logging-level", env_var="SERVICE_LOGGING_LEVEL", default="INFO")
    parser.add_argument("--grafana-endpoint", env_var="GRAFANA_ENDPOINT")
    parser.add_argument("--grafana-results-url", env_var="GRAFANA_RESULTS_URL")
    parser.add_argument("--grafana-op-metrics-dashboard-uid", env_var="GRAFANA_OP_METRICS_DASHBOARD_UID")

    parsed_args, _ = parser.parse_known_args(args)
    return WatcherServiceConfig(
        kubernetes_namespace_of_running_jobs=parsed_args.kubernetes_namespace_of_running_jobs,
        kubeconfig=parsed_args.kubeconfig,
        logging_level=parsed_args.service_logging_level,
        grafana_endpoint=parsed_args.grafana_endpoint,
        grafana_results_url=parsed_args.grafana_results_url,
        grafana_op_metrics_dashboard_uid=parsed_args.grafana_op_metrics_dashboard_uid,
    )
