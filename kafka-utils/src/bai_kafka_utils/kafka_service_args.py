import argparse
import os

from configargparse import ArgParser

from bai_kafka_utils.kafka_service import KafkaServiceConfig


def get_kafka_service_config(program_name: str, cmd_args: str) -> KafkaServiceConfig:
    parser = create_kafka_service_parser(program_name)
    args, _ = parser.parse_known_args(cmd_args, env_vars=os.environ)
    return KafkaServiceConfig(
        consumer_topic=args.consumer_topic,
        producer_topic=args.producer_topic,
        consumer_group_id=args.consumer_group_id,
        bootstrap_servers=args.bootstrap_servers,
        cmd_submit_topic=args.cmd_submit_topic,
        cmd_return_topic=args.cmd_return_topic,
        logging_level=args.logging_level,
        status_topic=args.status_topic,
    )


def create_kafka_service_parser(program_name: str) -> ArgParser:
    def create_split_action(delimiter: str):
        class customAction(argparse.Action):
            def __call__(self, parser, args, values, option_string=None):
                setattr(args, self.dest, values.split(delimiter))

        return customAction

    parser = ArgParser(auto_env_var_prefix="", prog=program_name)

    parser.add_argument("--consumer-topic", env_var="CONSUMER_TOPIC", required=True)

    parser.add_argument("--producer-topic", env_var="PRODUCER_TOPIC", required=True)

    parser.add_argument(
        "--bootstrap-servers",
        env_var="KAFKA_BOOTSTRAP_SERVERS",
        default="localhost:9092",
        action=create_split_action(","),
    )

    parser.add_argument("--consumer-group-id", env_var="CONSUMER_GROUP_ID")

    parser.add_argument("--cmd-submit-topic", env_var="CMD_SUBMIT_TOPIC", default="CMD_SUBMIT")

    parser.add_argument("--cmd-return-topic", env_var="CMD_RETURN_TOPIC", default="CMD_RETURN")

    parser.add_argument("--status-topic", env_var="STATUS_TOPIC", default="BAI_APP_STATUS")

    parser.add_argument("--logging-level", env_var="LOGGING_LEVEL", default="INFO")

    return parser
