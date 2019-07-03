import json
import logging
import os
import selectors
import stat
from contextlib import ExitStack
from json import JSONDecodeError

import io
import signal
from typing import List, Iterable, Tuple

from bai_metrics_pusher.args import InputValue
from bai_metrics_pusher.backends import create_backend
from bai_metrics_pusher.backends.backend_interface import Backend
from bai_metrics_pusher.kubernetes_pod_watcher import start_kubernetes_pod_watcher

logger = logging.getLogger(__name__)


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

    def opener(path, flags):
        # Opens the FIFO in non-blocking mode
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK)

    # Use line buffering (buffering=1) since we want every line to be read as soon as possible. Since the delimiter of
    # our JSON is a line ending, then this is the optimal way of configuring the stream.
    return io.open(pathname, "r", buffering=1, opener=opener)


def collect_lines(fileobj) -> Iterable[str]:
    while True:
        line = fileobj.readline()
        if line == "":  # EOF
            break
        yield line


def generate_lines_from_fifos(fifo_filenames: List[str]):
    """
    A generator that reads all lines from the files specified by :param(fifo_filenames) using `fifo.readline()`.

    Each file will be created as a FIFO (https://docs.python.org/3/library/os.html#os.mkfifo) by the method _get_fifo().

    The default behaviour of named pipes is to block as soon as the file is open for reading, but this is NOT desired
    here since we want to generate lines from all FIFOs as soon as possible.

    The trick is to use non-blocking IO and the `selectors` module:

    - Each FIFO is opened for reading in non-blocking mode: see _get_fifo()
    - Register for EVENT_READ events on each FIFO using a "selector"
    - A FIFO was closed on the "writing end" when:
        - There was an EVENT_READ
        - The result of `fifo.readline()` is empty

    :param fifo_filenames:
    :return:
    """
    with ExitStack() as stack:
        selector: selectors.DefaultSelector = stack.enter_context(selectors.DefaultSelector())

        for filename in fifo_filenames:
            fifo = stack.enter_context(_get_fifo(filename))
            logger.debug(f"Fifo {filename} opened")
            selector.register(fifo, selectors.EVENT_READ)

        while selector.get_map():
            logger.debug("Waiting for data to be ready")
            events: List[Tuple[selectors.SelectorKey, int]] = selector.select()
            for key, event in events:
                fifo = key.fileobj
                lines = list(collect_lines(fifo))
                if not lines:
                    logger.debug(f"FIFO {fifo.name} is closed on the writing side")
                    selector.unregister(fifo)
                else:
                    yield from lines


def listen_to_fifos_and_emit_metrics(fifo_filenames: List[str], backend: Backend):
    """
    :param fifo_filenames: The fifo filenames
    :param backend: The backend used to emit metrics
    """
    for line in generate_lines_from_fifos(fifo_filenames):
        metrics = _deserialize(line)
        backend.emit(metrics)


def start_loop(metrics_pusher_input: InputValue):
    backend = create_backend(metrics_pusher_input.backend, **metrics_pusher_input.backend_args)

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

        listen_to_fifos_and_emit_metrics(metrics_pusher_input.fifo_filenames, backend)
    except (SigtermReceived, KeyboardInterrupt) as e:
        logger.info(f"{type(e).__name__} received")
    finally:
        # TODO: Do I need to finish reading the FIFO contents?
        logger.info("Closing backend")
        backend.close()
