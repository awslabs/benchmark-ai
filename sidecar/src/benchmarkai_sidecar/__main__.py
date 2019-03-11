#!/usr/bin/env python

from benchmarkai_sidecar import listen_to_fifo_and_emit_metrics, FIFO_FILEPATH


def main():
    # We import only inside the `main()` method to ensure we configure everything to ensure nothing from the global
    # context runs before we configure logging
    import logging
    import os
    import sys

    # Configure logging
    logging_streams = {
        "stdout": sys.stdout,
        "stderr": sys.stderr
    }
    stream = logging_streams[os.environ.get("LOGGING_STREAM", "stderr").lower()]
    logging.basicConfig(
        stream=stream,
        level=os.environ.get("LOGGING_LEVEL", "INFO").upper(),
    )

    # For easier local testing we remove the file, it is harmless either way
    if os.path.exists(FIFO_FILEPATH):
        os.unlink(FIFO_FILEPATH)
    listen_to_fifo_and_emit_metrics()
    # Start the app
    logger = logging.getLogger("bai-sidecar")

    logger.info("Starting app")


if __name__ == "__main__":
    main()
