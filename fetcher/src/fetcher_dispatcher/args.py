import json

from bai_kafka_utils.kafka_service_args import create_kafka_service_parser
from fetcher_dispatcher import SERVICE_NAME

ZOOKEEPER_ENSEMBLE_HOSTS_ENV = "ZOOKEEPER_ENSEMBLE_HOSTS"

FETCHER_NODE_SELECTOR_ENV = "FETCHER_NODE_SELECTOR"

FETCHER_JOB_IMAGE_ENV = "FETCHER_JOB_IMAGE"

S3_DATASET_BUCKET_ENV = "S3_DATASET_BUCKET"

KUBECONFIG_ENV = "KUBECONFIG"

FETCHER_JOB_NODE_SELECTOR_ARG = "--fetcher-job-node-selector"

FETCHER_JOB_IMAGE_ARG = "--fetcher-job-image"

KUBECONFIG_ARG = "--kubeconfig"

S3_DATA_SET_BUCKET_ARG = "--s3-data-set-bucket"

ZOOKEEPER_ENSEMBLE_HOSTS_ARG = "--zookeeper-ensemble-hosts"


def get_args(args):
    parser = create_kafka_service_parser(SERVICE_NAME)

    parser.add_argument(ZOOKEEPER_ENSEMBLE_HOSTS_ARG,
                        env_var=ZOOKEEPER_ENSEMBLE_HOSTS_ENV,
                        default="localhost:2181")

    parser.add_argument(S3_DATA_SET_BUCKET_ARG,
                        env_var=S3_DATASET_BUCKET_ENV,
                        required=True)

    parser.add_argument(KUBECONFIG_ARG,
                        env_var=KUBECONFIG_ENV)

    parser.add_argument(FETCHER_JOB_IMAGE_ARG,
                        env_var=FETCHER_JOB_IMAGE_ENV,
                        required=True)

    parser.add_argument(FETCHER_JOB_NODE_SELECTOR_ARG,
                        env_var=FETCHER_NODE_SELECTOR_ENV,
                        type=json.loads)

    parsed_args = parser.parse_args(args)
    return parsed_args
