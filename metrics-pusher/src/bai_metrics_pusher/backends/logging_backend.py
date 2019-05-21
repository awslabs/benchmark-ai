import logging
import json
from typing import Dict

from bai_metrics_pusher.backends.backend_interface import Backend, AcceptedMetricTypes

logger = logging.getLogger("backend.stdout")


class LoggingBackend(Backend):
    def __init__(self, job_id: str):
        self.job_id = job_id

    def emit(self, metrics: Dict[str, AcceptedMetricTypes]):
        logger.info(json.dumps(metrics))

    def close(self):
        pass
