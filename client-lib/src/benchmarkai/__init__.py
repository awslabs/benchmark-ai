import json
import os
import six
if six.PY2:
    from collections import Mapping
else:
    from collections.abc import Mapping

__fifo = None


class FifoNotCreatedInTimeError(Exception):
    pass


def _sleep(seconds):
    # So that tests can mock this method more easily. It is possible to mock the `time.sleep()` method, however, when
    # a debugger is attached then this method is called by many other modules. Having a separate method makes it easier
    # to get the right results when debugging.
    import time
    time.sleep(seconds)


def _getfifo():
    global __fifo
    if __fifo is None:
        pathname = os.environ.get("BENCHMARK_AI_FIFO_FILEPATH", "/tmp/benchmark-ai-fifo")

        max_wait_time = float(os.environ.get("BENCHMARK_AI_FIFO_MAX_WAIT_TIME", "10"))
        step_time = float(os.environ.get("BENCHMARK_AI_FIFO_WAIT_TIME_STEP", "0.5"))

        waited = 0
        while not os.path.exists(pathname):
            if waited > max_wait_time:
                raise FifoNotCreatedInTimeError()

            # Other process has not created the FIFO yet. This should NOT usually happen.
            # This situation arises if the benchmark (this process) called emit() before the other process was able to
            # create the fifo.
            print("[benchmark ai] DEBUG - Other process has NOT created the FIFO yet,"
                  " sleeping for %f seconds" % step_time)
            _sleep(step_time)
            waited += step_time

        import io
        __fifo = io.open(pathname, "w")

        import atexit
        atexit.register(__fifo.close)
    return __fifo


def _send(fifo, s):
    fifo.write(s + "\n")
    fifo.flush()


def _serialize(metrics):
    if not isinstance(metrics, Mapping):
        raise TypeError("The parameter `metrics` should be a dictionary, but it is {}".format(type(metrics)))
    if len(metrics) == 0:
        raise ValueError("The parameter `metrics` is empty")
    return json.dumps(metrics)


def _emit_to_fifo(metrics):
    s = _serialize(metrics)
    file = _getfifo()
    _send(file, s)


def _emit_to_stdout(metrics):
    s = _serialize(metrics)
    print(s)


# Make an `if` at import time so that user doesn't pay the price of a dict lookup on EVERY call to emit()
configured_emitter = os.environ.get("BENCHMARK_AI", "stdout").lower()
if configured_emitter == "fifo":
    emit = _emit_to_fifo
elif configured_emitter == "stdout":
    emit = _emit_to_stdout
else:
    raise ValueError("Unsupported emitter: %s" % configured_emitter)
