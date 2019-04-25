import json

from fetcher_dispatcher import SERVICE_NAME
from bai_kafka_utils.kafka_service import create_kafka_service_parser

def get_args(args):
    parser = create_kafka_service_parser(SERVICE_NAME)

    parser.add_argument("--zookeeper-ensemble-hosts",
                        env_var="ZOOKEEPER_ENSEMBLE_HOSTS",
                        default="localhost:2181")

    parser.add_argument("--s3-data-set-bucket",
                        env_var="S3_DATASET_BUCKET",
                        required=True)

    parser.add_argument("--kubeconfig",
                        env_var="KUBECONFIG")

    parser.add_argument("--fetcher-job-image",
                        env_var="FETCHER_JOB_IMAGE")

    parser.add_argument("--fetcher-job-node-selector",
                        env_var="FETCHER_NODE_SELECTOR",
                        type=json.loads)

    parsed_args = parser.parse_args(args)
    return parsed_args
