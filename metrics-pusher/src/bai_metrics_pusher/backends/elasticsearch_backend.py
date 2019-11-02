#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import Dict

import datetime
import json
import logging
from elasticsearch import Elasticsearch

from bai_metrics_pusher.backends.backend_interface import Backend, AcceptedMetricTypes

logger = logging.getLogger("backend.elasticsearch")


class ElasticsearchBackend(Backend):
    def __init__(
        self, action_id: str, client_id: str, labels: Dict[str, str], *, hostname: str = "localhost", port: int = 9200
    ):
        self.action_id = action_id
        self.client_id = client_id
        self.labels = labels
        verify_certs = True

        # Easier local testing
        if hostname == "localhost":
            verify_certs = False

        self.es = Elasticsearch([dict(host=hostname, port=port, verify_certs=verify_certs, use_ssl=True)])

    def emit(self, metrics: Dict[str, AcceptedMetricTypes]):
        timestamp = datetime.datetime.utcnow().isoformat()
        doc = {
            "action-id": self.action_id,
            "client-id": self.client_id,
            **self.labels,
            "timestamp": timestamp,
            "metrics": metrics,
            "tracing": {"service": "metrics-pusher"},
        }
        r = self.es.index(index="job-metrics", doc_type="metric", body=json.dumps(doc))
        logger.debug("Response: %r", r)

    def close(self):
        pass
