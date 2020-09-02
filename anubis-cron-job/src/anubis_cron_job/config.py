#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import configargparse
import json

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class AnubisCronJobConfig:
    kafka_bootstrap_servers: List[str]
    producer_topic: str
    status_topic: str
    benchmark_event: Dict[str, Any]


def get_config(argv, env=None) -> AnubisCronJobConfig:

    parser = configargparse.ArgParser(
        description="Tool for generating single-benchmark runs from a periodic benchmark template"
    )

    parser.add(
        "--kafka-bootstrap-servers",
        type=lambda x: x.split(","),
        env_var="KAFKA_BOOTSTRAP_SERVERS",
        help="Comma separated list of kafka bootstrap servers",
        required=True,
    )

    parser.add(
        "--producer-topic",
        env_var="PRODUCER_TOPIC",
        help="The topic the executor listens to to spawn single-run jobs",
        required=True,
    )

    parser.add("--status-topic", env_var="STATUS_TOPIC", help="The status topic", required=True)

    parser.add(
        "--benchmark-event",
        type=json.loads,
        env_var="BENCHMARK_EVENT",
        help="A string containing the original event containing the periodic benchmark",
        required=True,
    )

    parsed_args, _ = parser.parse_known_args(argv, env_vars=env)
    return AnubisCronJobConfig(
        kafka_bootstrap_servers=parsed_args.kafka_bootstrap_servers,
        producer_topic=parsed_args.producer_topic,
        status_topic=parsed_args.status_topic,
        benchmark_event=parsed_args.benchmark_event,
    )
