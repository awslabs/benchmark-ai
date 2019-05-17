#!/usr/bin/env python


def main(argv=None):
    # We import only inside the `main()` method to ensure we configure everything so that nothing from the global
    # context runs before we configure logging
    import logging
    import os
    import sys

    # Configure logging
    logging_streams = {"stdout": sys.stdout, "stderr": sys.stderr}
    stream = logging_streams[os.environ.get("LOGGING_STREAM", "stderr").lower()]
    logging.basicConfig(stream=stream, level=os.environ.get("LOGGING_LEVEL", "INFO").upper())

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
