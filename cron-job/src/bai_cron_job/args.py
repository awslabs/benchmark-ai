import configargparse
import json


def get_args(argv, env=None):

    parser = configargparse.ArgParser(
        description="Tool for generating single-bench mark runs from a periodic benchmark template"
    )

    parser.add(
        "--kafka-bootstrap-servers",
        type=lambda x: x.split(","),
        env_var="KAFKA_BOOTSTRAP_SERVERS",
        help="Comma separated list of kafka bootstrap servers",
        required=True
    )

    parser.add(
        "--producer-topic",
        env_var="PRODUCER_TOPIC",
        help="The topic the executor listens to to spawn single-run jobs",
        required=True
    )

    parser.add(
        "--benchmark-event",
        type=json.loads,
        env_var="BENCHMARK_EVENT",
        help="A string containing the original event containing the periodic benchmark",
        required=True
    )

    parsed_args, _ = parser.parse_args(argv, env_vars=env)
    return parsed_args
