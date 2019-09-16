import logging

__version__ = "0.1.0"
NAME = "inference-benchmark"
DESCRIPTION = "Executes inference benchmarks"

logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())
app_logger = logging.getLogger(NAME)
