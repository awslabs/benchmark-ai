from dataclasses import dataclass

from configargparse import ArgParser

from bai_watcher import SERVICE_NAME


@dataclass
class WatcherServiceConfig:
    pass


def get_watcher_service_config(args) -> WatcherServiceConfig:
    parser = ArgParser(auto_env_var_prefix="", prog=SERVICE_NAME)

    parsed_args, _ = parser.parse_known_args(args)
    return WatcherServiceConfig()
