import argparse

from configargparse import ArgParser

LOGGING_LEVEL_ENV = "LOGGING_LEVEL"

CONSUMER_GROUP_ID_ENV = "CONSUMER_GROUP_ID"

BOOTSTRAP_SERVERS_ENV = "KAFKA_BOOTSTRAP_SERVERS"

PRODUCER_TOPIC_ENV = 'PRODUCER_TOPIC'

CONSUMER_TOPIC_ENV = 'CONSUMER_TOPIC'

LOGGING_LEVEL_ARG = "--logging-level"

CONSUMER_GROUP_ID_ARG = "--consumer-group-id"

BOOTSTRAP_SERVERS_ARG = "--bootstrap-servers"

PRODUCER_TOPIC_ARG = "--producer-topic"

CONSUMER_TOPIC_ARG = "--consumer-topic"


def create_kafka_service_parser(program_name: str) -> ArgParser:
    def create_split_action(delimiter: str):
        class customAction(argparse.Action):
            def __call__(self, parser, args, values, option_string=None):
                setattr(args, self.dest, values.split(delimiter))

        return customAction

    parser = ArgParser(auto_env_var_prefix="",
                       prog=program_name)

    parser.add_argument(CONSUMER_TOPIC_ARG,
                        env_var=CONSUMER_TOPIC_ENV,
                        required=True)

    parser.add_argument(PRODUCER_TOPIC_ARG,
                        env_var=PRODUCER_TOPIC_ENV,
                        required=True)

    parser.add_argument(BOOTSTRAP_SERVERS_ARG,
                        env_var=BOOTSTRAP_SERVERS_ENV,
                        default="localhost:9092",
                        action=create_split_action(','))

    parser.add_argument(CONSUMER_GROUP_ID_ARG,
                        env_var=CONSUMER_GROUP_ID_ENV)

    parser.add_argument(LOGGING_LEVEL_ARG,
                        env_var=LOGGING_LEVEL_ENV,
                        default="INFO")

    return parser
