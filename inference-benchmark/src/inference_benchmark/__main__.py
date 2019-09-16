import sys

from inference_benchmark import app_logger
from inference_benchmark.args import get_inference_benchmark_config
from inference_benchmark.inference_benchmark import InferenceBenchmark, InferenceBenchmarkFailedError

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
    main()
