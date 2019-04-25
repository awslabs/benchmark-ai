import json

import argparse
import configargparse


def get_args(argv):
    def create_split_action(delimiter: str):
        class customAction(argparse.Action):
            def __call__(self, parser, args, values, option_string=None):
                setattr(args, self.dest, values.split(delimiter))

        return customAction

    parser = configargparse.ArgumentParser(auto_env_var_prefix="", prog="fetcher-dispatcher")
    parser.add_argument("--consumer-topic", env_var='CONSUMER_TOPIC', required=True)
    parser.add_argument("--producer-topic", env_var='PRODUCER_TOPIC', required=True)
    parser.add_argument("--bootstrap-servers", env_var="KAFKA_BOOTSTRAP_SERVERS", default="localhost:9092",
                        action=create_split_action(','))
    parser.add_argument("--zookeeper-ensemble-hosts", env_var="ZOOKEEPER_ENSEMBLE_HOSTS",
                        default="localhost:2181")
    parser.add_argument("--s3-data-set-bucket", env_var="S3_DATASET_BUCKET", required=True)
    parser.add_argument("--kubeconfig", env_var="KUBECONFIG")
    parser.add_argument("--fetcher-job-image", env_var="FETCHER_JOB_IMAGE")
    parser.add_argument("--fetcher-job-node-selector", env_var="FETCHER_NODE_SELECTOR", type=json.loads)
    parser.add_argument("--consumer-group-id", env_var="CONSUMER_GROUP_ID")

    parser.add_argument("--logging-level", env_var="LOGGING_LEVEL", default="INFO")

    return parser.parse_args(argv)
