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

    import argparse
    parser = argparse.ArgumentParser(prog="benchmarkai_metrics_pusher")
    parser.add_argument("job-id")

    from benchmarkai_metrics_pusher.elasticsearch_backend import ElasticsearchBackend
    from benchmarkai_metrics_pusher.logging_backend import LoggingBackend
    backends = {
        "stdout": LoggingBackend,
        "elasticsearch": ElasticsearchBackend,
    }
    parser.add_argument("--backend", default="stdout", choices=list(backends.keys()))
    args = parser.parse_args(argv)

    # Get the backend args
    backend_args = {}
    for key, value in os.environ.items():
        if key.startswith("BACKEND_ARG_"):
            argname = key.lstrip("BACKEND_ARG_")
            backend_args[argname] = value
    backend = backends[args.backend](getattr(args, "job-id"), **backend_args)

    # Start the loop

    from benchmarkai_metrics_pusher import listen_to_fifo_and_emit_metrics
    from benchmarkai_metrics_pusher.kubernetes_pod_watcher import start_kubernetes_pod_watcher
    import signal

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
        start_kubernetes_pod_watcher(os.environ["POD_NAME"], os.environ["POD_NAMESPACE"])

        listen_to_fifo_and_emit_metrics(backend)
    except SigtermReceived:
        # TODO: Do I need to finish reading the FIFO contents?
        logger.info("Pod is terminated, exiting")


if __name__ == "__main__":
    main()
