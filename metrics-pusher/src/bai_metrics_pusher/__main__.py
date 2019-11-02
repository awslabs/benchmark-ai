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
#!/usr/bin/env python


def main(argv=None):
    # We import only inside the `main()` method to ensure we configure everything so that nothing from the global
    # context runs before we configure logging
    import logging
    import os
    import sys

    # Configure logging
    from bai_kafka_utils.logging import configure_logging

    logging_streams = {"stdout": sys.stdout, "stderr": sys.stderr}
    stream = logging_streams[os.environ.get("LOGGING_STREAM", "stderr").lower()]
    configure_logging(level=os.environ.get("LOGGING_LEVEL", "INFO").upper(), stream=stream)

    # Start the app
    logger = logging.getLogger("metrics-pusher")

    logger.info("Starting app")

    from bai_metrics_pusher.args import get_input

    metrics_pusher_input = get_input(argv)
    logger.info("Input is %s", metrics_pusher_input)

    # Start the loop
    from bai_metrics_pusher.loop import start_loop

    start_loop(metrics_pusher_input)


if __name__ == "__main__":
    main()
