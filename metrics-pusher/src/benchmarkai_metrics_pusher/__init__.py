import io
import os
import stat
import logging
import json
from typing import Dict, Callable
from json import JSONDecodeError


logger = logging.getLogger("metrics-pusher")
FIFO_FILEPATH = os.environ.get("BENCHMARK_AI_FIFO_FILEPATH", "/tmp/benchmark-ai-fifo")


def _deserialize(line):
    try:
        return json.loads(line)
    except JSONDecodeError:
        # Swallow the exception since we don't want to stop processing if the line couldn't be deserialized.
        logger.exception("Error when processing line with json.")


def _get_fifo(pathname):
    if os.path.exists(pathname):
        logger.info("Opening fifo at %s", pathname)
        if not stat.S_ISFIFO(os.stat(pathname).st_mode):
            raise RuntimeError("File '%s' is not a FIFO" % pathname)
    else:
        logger.info("Creating fifo at %s", pathname)
        os.mkfifo(pathname)

    # Use line buffering (buffering=1) since we want every line to be read as soon as possible. Since the delimiter of
    # our JSON is a line ending, then this is the optimal way of configuring the stream.
    return io.open(pathname, "r", buffering=1)


def listen_to_fifo_and_emit_metrics(emit: Callable[[Dict], None]):
    with _get_fifo(FIFO_FILEPATH) as fifo:
        while True:
            logger.debug("Reading line from fifo")
            line = fifo.readline()
            if line == "":  # The client side sent an EOF
                break
            metrics = _deserialize(line)
            emit(metrics)
