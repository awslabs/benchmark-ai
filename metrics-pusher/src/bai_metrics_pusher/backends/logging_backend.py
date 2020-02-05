import logging
import json
from typing import Dict

from bai_metrics_pusher.backends.backend_interface import Backend, AcceptedMetricTypes

logger = logging.getLogger("backend.stdout")


class LoggingBackend(Backend):
    def __init__(self, labels: Dict[str, str]):
        self.labels = labels

    def emit(self, metrics: Dict[str, AcceptedMetricTypes]):
        metrics["labels"] = self.labels
        logger.info(json.dumps(metrics))

    def close(self):
        pass
