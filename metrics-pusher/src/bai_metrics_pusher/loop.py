import io
import os
import stat
import logging
import json
import signal
from json import JSONDecodeError
from bai_metrics_pusher.backends import create_backend
from bai_metrics_pusher.args import InputValue
from bai_metrics_pusher.backends.backend_interface import Backend
from bai_metrics_pusher.kubernetes_pod_watcher import start_kubernetes_pod_watcher


logger = logging.getLogger(__name__)
FIFO_FILEPATH = os.environ.get("BENCHMARK_AI_FIFO_FILEPATH", "/tmp/benchmark-ai/fifo")


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


def listen_to_fifo_and_emit_metrics(backend: Backend):
    with _get_fifo(FIFO_FILEPATH) as fifo:
        while True:
            logger.debug("Reading line from fifo")
            line = fifo.readline()
            if line == "":  # The client side sent an EOF
                break
            metrics = _deserialize(line)
            backend.emit(metrics)


def start_loop(metrics_pusher_input: InputValue):
    backend = create_backend(
        metrics_pusher_input.backend, metrics_pusher_input.pod_labels, **metrics_pusher_input.backend_args
    )

    class SigtermReceived(Exception):
        pass

    try:

        def stop_loop(signum, frame):
            # An exception is being used as flow control here. The reason is because when opening a FIFO it blocks
            # while both sides haven't opened it yet.
            #
            # The call to fifo.read() also blocks, but when the code reaches that point the FIFO has already been opened
            # from the client-library side. From this point on, there is no need to worry about this program blocking
            # forever because there are guarantees that the FIFO file will be closed from the client-library side,
            # either by the client-library code, or the kernel.
            #
            # An alternative and more efficient approach to solving this problem would be to use an asyncio library
            # (eg.: Trio) to execute the IO operations required:
            # - read from FIFO
            # - post to backend
            # - watch the state of the Kubernetes POD
            raise SigtermReceived()

        signal.signal(signal.SIGTERM, stop_loop)

        if metrics_pusher_input.pod_name and metrics_pusher_input.pod_namespace:
            logger.info("Starting Pod watcher thread")
            start_kubernetes_pod_watcher(metrics_pusher_input.pod_name, metrics_pusher_input.pod_namespace)
        else:
            logger.info("Pod watcher thread will not start because either Pod or Namespace were not specified")

        listen_to_fifo_and_emit_metrics(backend)
    except SigtermReceived:
        logger.info("Sigterm received")
    finally:
        # TODO: Do I need to finish reading the FIFO contents?
        logger.info("Pod is terminated, exiting")
        backend.close()
