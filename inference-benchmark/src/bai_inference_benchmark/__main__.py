"""
This application starts and monitors an inference benchmark.
An inference benchmark is composed of two components: the inference server pod and the benchmark (client) pod.
The benchmark pod should start to fire inference requests against the inference server and generate benchmark metrics.

This application orchestrates this interaction. It is meant to run within a Kubernetes Job, to take advantage of
the restart and run-guarantees provided by the Job resource. This means that the execution should fail (the process
return code should be non-zero) in case of benchmark error.
"""
import sys

from bai_inference_benchmark import app_logger
from bai_inference_benchmark.args import get_inference_benchmark_config
from bai_inference_benchmark.inference_benchmark import InferenceBenchmark, InferenceBenchmarkFailedError

logger = app_logger.getChild(__name__)


def main(argv=None):
    inference_benchmark = InferenceBenchmark(get_inference_benchmark_config(argv))

    try:
        inference_benchmark.execute()
    except InferenceBenchmarkFailedError as err:
        logger.info(f"Benchmark failed: '{err}'")
        sys.exit(1)

    logger.info("Benchmark completed successfully")


if __name__ == "__main__":
    main(sys.argv)
