from dataclasses import dataclass, field

from configargparse import ArgParser
from typing import Optional

EXP_MULTIPLIER_MS = 1000

MAX_ATTEMPTS = 5

MAX_WAIT_MS = 60 * 5 * 1000


@dataclass
class RetryConfig:
    max_attempts: Optional[int] = None
    exp_max: Optional[int] = None
    exp_multiplier: Optional[int] = None


@dataclass
class FetcherJobConfig:
    src: str
    dst: str
    logging_level: Optional[str] = None
    md5: Optional[str] = None
    zk_node_path: Optional[str] = None
    zookeeper_ensemble_hosts: Optional[str] = None
    retry: Optional[RetryConfig] = field(default_factory=RetryConfig)
    tmp_dir: Optional[str] = None


def get_fetcher_job_args(args, env_vars):
    parser = ArgParser(description="Downloads the dataset from http/ftp/s3 to internal s3")
    parser.add_argument("--src", required=True, help="Source", default=None)
    parser.add_argument("--dst", metavar="dst", required=True, help="Destination", default=None)
    parser.add_argument("--md5", help="MD5 hash", default=None)
    parser.add_argument("--zk-node-path", help="Zookeeper node to update", default=None)
    parser.add_argument("--zookeeper-ensemble-hosts", env_var="ZOOKEEPER_ENSEMBLE_HOSTS", default="localhost:2181")
    parser.add_argument("--logging-level", env_var="LOGGING_LEVEL", default="INFO")
    parser.add_argument("--retry-max-attempts", env_var="RETRY_MAX_ATTEMPTS", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--retry-exp-max", env_var="RETRY_EXP_MAX", type=int, default=MAX_WAIT_MS)
    parser.add_argument("--retry-exp-multiplier", env_var="RETRY_EXP_MULTIPLIER", type=int, default=EXP_MULTIPLIER_MS)
    parser.add_argument("--tmp-dir", env_var="TMP_DIR", type=str)
    parsed_args = parser.parse_args(args, env_vars=env_vars)

    return FetcherJobConfig(
        src=parsed_args.src,
        dst=parsed_args.dst,
        md5=parsed_args.md5,
        zk_node_path=parsed_args.zk_node_path,
        zookeeper_ensemble_hosts=parsed_args.zookeeper_ensemble_hosts,
        logging_level=parsed_args.logging_level,
        retry=RetryConfig(
            exp_max=parsed_args.retry_exp_max,
            exp_multiplier=parsed_args.retry_exp_multiplier,
            max_attempts=parsed_args.retry_max_attempts,
        ),
        tmp_dir=parsed_args.tmp_dir,
    )
