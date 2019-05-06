from dataclasses import dataclass

from configargparse import ArgParser

from bai_watcher import SERVICE_NAME


@dataclass
class WatcherServiceConfig:
    kubernetes_namespace: str = "default"
    kubeconfig: str = None


def get_watcher_service_config(args) -> WatcherServiceConfig:
    parser = ArgParser(auto_env_var_prefix="", prog=SERVICE_NAME)

    parser.add_argument("--kubernetes-namespace", default="default")
    parser.add_argument("--kubeconfig")

    parsed_args, _ = parser.parse_known_args(args)
    return WatcherServiceConfig(
        kubernetes_namespace=parsed_args.kubernetes_namespace, kubeconfig=parsed_args.kubeconfig
    )
