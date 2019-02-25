import os
import logging
import json
import io
from json import JSONDecodeError


FIFO_FILEPATH = os.environ.get("BENCHMARK_AI_FIFO_FILEPATH", "/tmp/benchmark-ai-fifo")


def _emit(metrics):
    # TODO: elastic search
    print("Emitting metrics: %s" % metrics)


def _deserialize(line):
    try:
        return json.loads(line)
    except JSONDecodeError:
        # Swallow the exception since we don't want to stop processing if the line couldn't be deserialized.
        logging.exception("Error when processing line with json.")


def _get_fifo(pathname):
    logging.info("Creating fifo")
    os.mkfifo(pathname)

    # Use line buffering (buffering=1) since we want every line to be read as soon as possible. Since the delimiter of
    # our JSON is a line ending, then this is the optimal way of configuring the stream.
    return io.open(pathname, "r", buffering=1)


def listen_to_fifo_and_emit_metrics():
    with _get_fifo(FIFO_FILEPATH) as fifo:
        while True:
            logging.debug("Reading line from fifo")
            line = fifo.readline()
            if line == "":  # The client side sent an EOF
                break
            metrics = _deserialize(line)
            _emit(metrics)
