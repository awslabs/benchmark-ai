A small library for publishing metrics when running a workflow using the Benchmark AI infrastructure.

# Installation

```
pip install benchmarkai-client-lib
```

# API

The library provides a single method:

```
def emit(metrics: Dict[str, float])
```

PS: This library also works with Python 2, which has no type system.

## Example usage

```python
from benchmarkai import emit

def my_fancy_benchmark():
    import time
    begin = time.time()
    for epoch in range(100):
        execute_training()
    elapsed_time = time.time() - begin
    emit({"alexnet.batchsize16.latency": elapsed_time})
```

## Performance

As the author you don't need to worry about `emit()` being slow since it does 2 things:

- serializes `metrics` into JSON
- writes this string into a file (see the internal details)

So it will be as slow as these operations can be, which are quite fast.

## Accepted values

The dictionary provided by the `metrics` parameter is in the form:

`"metric-name" => value`

- `metric-name` is a `string`
- `value` is a `float`

# Running tests

To set up the environment to run the tests, the file `test-environment.yml` is provided. This conda environment file
has all dependencies required to run the tests.

```
$ conda env create -f test-environment.yml
$ conda activate benchmark-ai-client-library-tests
$ tox
```

# Internal details

## Modes

The library can be used in these modes as of now:

1. Stdout printing (this is the **default** mode)
1. Benchmark AI infrastructure

To control which behavior is desired, the environment variable `BENCHMARK_AI` can be set to one of the values:

- `stdout`: The **default** mode. In this configuration, the `emit()` method is equivalent to:
    ```python
    def emit(metrics):
        import json
        print(json.dumps(metrics))
    ```

- `fifo`: When running inside Benchmark AI infrastructure this is the mode used.

### Fifo mode

In this mode, the `emit()` method writes JSON string to a file that was created as a 
[named pipe](https://docs.python.org/3.7/library/os.html#os.mkfifo). It does **NOT** write to `stdout`.

Keep in mind that the client library does **NOT** create the *named pipe* file, this is delegated to the
"daemon process", which will be running alongside the benchmark process in the Benchmark AI infrastructure.

The daemon process is responsible to:

- create the *named pipe*
- read the contents from this pipe
- post the contents of this pipe to the metrics servers (eg.: Elastic Search, Cloudwatch, etc.)

The first time that `emit()` is called, it checks for the existence of the file and uses that. If it doesn't exist, it
waits for some time before giving up and throwing an exception `FifoNotCreatedInTimeError`.

#### Fifo mode configurations

These environment variables control the behavior of the client library:

- `BENCHMARK_AI_FIFO_FILEPATH`: The path to the file that will be created as a *named pipe*.
                                Default value: `/tmp/benchmark-ai-fifo`
- `BENCHMARK_AI_FIFO_MAX_WAIT_TIME`: The maximum amount of time that the client library will wait for the
                                     *named pipe file* to be created.
                                     Type is **float**, unit is **seconds**, default value: `10`.
- `BENCHMARK_AI_FIFO_WAIT_TIME_STEP`: The amount of time between each check that the client library will wait before
                                      checking for the existence of the *named pipe file* again.
                                      Type is **float**, unit is **seconds**, default value: `0.5`.

**IMPORTANT**: These environment variables are for internal usage of the Benchmark AI infrastructure. They are listed
               here for documentation purposes only.
