import logging
import json
from typing import Dict

from bai_metrics_pusher.backends.backend_interface import Backend, AcceptedMetricTypes

logger = logging.getLogger("backend.stdout")


class LoggingBackend(Backend):
    def __init__(self, pod_labels: Dict[str, str]):
        self.pod_labels = pod_labels

    def emit(self, metrics: Dict[str, AcceptedMetricTypes]):
        metrics["labels"] = self.pod_labels
        logger.info(json.dumps(metrics))

    def close(self):
        pass
