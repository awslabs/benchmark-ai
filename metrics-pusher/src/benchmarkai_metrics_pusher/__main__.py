#!/usr/bin/env python


def main(argv=None):
    # We import only inside the `main()` method to ensure we configure everything so that nothing from the global
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

    # Start the app
    logger = logging.getLogger("metrics-pusher")

    logger.info("Starting app")

    from benchmarkai_metrics_pusher.input_values import get_input
    metrics_pusher_input = get_input(argv)

    # Start the loop
    start_loop(logger, metrics_pusher_input)


def start_loop(logger, metrics_pusher_input):
    """
    :type metrics_pusher_input: benchmarkai_metrics_pusher.input_values.InputValue
    :param logger:
    :return:
    """
    from benchmarkai_metrics_pusher import listen_to_fifo_and_emit_metrics
    from benchmarkai_metrics_pusher.kubernetes_pod_watcher import start_kubernetes_pod_watcher
    from benchmarkai_metrics_pusher.backends import create_backend
    import signal

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
            start_kubernetes_pod_watcher(metrics_pusher_input.pod_name, metrics_pusher_input.pod_namespace)

        listen_to_fifo_and_emit_metrics(backend)
    except SigtermReceived:
        # TODO: Do I need to finish reading the FIFO contents?
        logger.info("Pod is terminated, exiting")


if __name__ == "__main__":
    main()
