#!/usr/bin/env python
import logging
import os
import sys

from benchmarkai_sidecar import listen_to_fifo_and_emit_metrics, FIFO_FILEPATH


def main():
    logging_streams = {
        "stdout": sys.stdout,
        "stderr": sys.stderr
    }
    stream = logging_streams[os.environ.get("LOGGING_STREAM", "stderr").lower()]
    logging.basicConfig(
        stream=stream,
        level=os.environ.get("LOGGING_LEVEL", "INFO").upper(),
    )
    logging.info("Starting app")

    # For easier local testing we remove the file, it is harmless either way
    if os.path.exists(FIFO_FILEPATH):
        os.unlink(FIFO_FILEPATH)
    listen_to_fifo_and_emit_metrics()


if __name__ == "__main__":
    main()
