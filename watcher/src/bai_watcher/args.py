from dataclasses import dataclass

from configargparse import ArgParser

from bai_watcher import SERVICE_NAME


@dataclass
class WatcherServiceConfig:
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

    parsed_args, _ = parser.parse_known_args(args)
    return WatcherServiceConfig(
        kubernetes_namespace_of_running_jobs=parsed_args.kubernetes_namespace_of_running_jobs,
        kubeconfig=parsed_args.kubeconfig,
        logging_level=parsed_args.service_logging_level,
    )
