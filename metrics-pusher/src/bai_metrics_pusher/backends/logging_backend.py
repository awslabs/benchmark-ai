import logging
import json

logger = logging.getLogger("backend.stdout")


class LoggingBackend:
    def __init__(self, job_id):
        self.job_id = job_id

    def __call__(self, metrics):
        logger.info(json.dumps(metrics))
