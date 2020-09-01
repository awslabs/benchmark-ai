#!/usr/bin/env python

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

# The default pattern which would in most cases be just accuracy is
# {"name":"accuracy", "pattern":"YWNjdXJhY3k9KFstK10/XGQqXC5cZCt8XGQrKQ=="}
# where YWNjdXJhY3k9KFstK10/XGQqXC5cZCt8XGQrKQ== is base64 encoded: accuracy=([-+]?\d*\.\d+|\d+)


def main(argv=None):
    import logging
    import os
    import sys

    import configargparse
    from kubernetes import config

    parser = configargparse.ArgumentParser(
        auto_env_var_prefix="ANUBIS_",
        default_config_files=["~/.anubis/metrics_extractor_config"],
        args_for_setting_config_path=["-c", "--config"],
        config_arg_is_required=False,
    )

    parser.add_argument("-s", "--logging-stream", default="stderr")
    parser.add_argument("-l", "--logging-level", default="INFO")
    parser.add_argument("-p", "--pod-name", required=True)
    parser.add_argument("-n", "--pod-namespace", default="default")
    parser.add_argument("-t", "--pod-container", default="benchmark")
    parser.add_argument(
        "-m",
        "--metrics",
        required=True,
        help="JSON of metrics spec. Note that pattern needs to be base64 encoded as JSON has issues "
        "with escape characters.",
    )

    args = parser.parse_args(argv)

    # Configure logging
    from bai_kafka_utils.logging import configure_logging

    logging_streams = {"stdout": sys.stdout, "stderr": sys.stderr}
    stream = logging_streams[args.logging_stream.lower()]
    configure_logging(level=args.logging_level.upper(), stream=stream)

    # Start the app
    logger = logging.getLogger("metrics-extractor")

    logger.info("Starting app")

    from anubis_metrics_extractor.log_listener import LogExtractor, LogExtractorOptions, EnvironmentReader

    env_reader = EnvironmentReader(args.metrics)
    metrics = env_reader.get_metrics()
    options = LogExtractorOptions(
        pod_name=args.pod_name, pod_namespace=args.pod_namespace, pod_container=args.pod_container, metrics=metrics
    )
    extractor = LogExtractor(options)

    if "KUBECONFIG" in os.environ:
        kubeconfig = os.path.expanduser(os.environ.get("KUBECONFIG"))
        logger.info(f"Loading KUBECONFIG from {kubeconfig}")
        config.load_kube_config(kubeconfig)
    else:
        logger.info("Loading in cluster KUBECONFIG")
        config.load_incluster_config()

    logger.info("Starting listening")
    extractor.listen()


if __name__ == "__main__":
    main()
