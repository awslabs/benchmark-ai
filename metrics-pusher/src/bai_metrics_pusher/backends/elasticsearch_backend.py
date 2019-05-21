from typing import Dict

import datetime
import json
import logging
from elasticsearch import Elasticsearch

from bai_metrics_pusher.backends.backend_interface import Backend, AcceptedMetricTypes

logger = logging.getLogger("backend.elasticsearch")


class ElasticsearchBackend(Backend):
    def __init__(self, job_id: str, *, hostname: str = "localhost", port: int = 9200):
        self.job_id = job_id

        verify_certs = True

        # Easier local testing
        if hostname == "localhost":
            verify_certs = False

        self.es = Elasticsearch([dict(host=hostname, port=port, verify_certs=verify_certs, use_ssl=True)])

    def emit(self, metrics: Dict[str, AcceptedMetricTypes]):
        timestamp = datetime.datetime.utcnow().isoformat()
        doc = {
            "job-id": self.job_id,
            "timestamp": timestamp,
            "metrics": metrics,
            "tracing": {"service": "metrics-pusher"},
        }
        r = self.es.index(index="job-metrics", doc_type="metric", body=json.dumps(doc))
        logger.debug("Response: %r", r)

    def close(self):
        pass
