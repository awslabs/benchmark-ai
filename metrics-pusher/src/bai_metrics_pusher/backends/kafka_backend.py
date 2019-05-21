from typing import Optional, Dict, List

import datetime
import logging
import dataclasses
from dataclasses_json import dataclass_json

from bai_kafka_utils.kafka_client import create_kafka_producer

logger = logging.getLogger("backend.kafka")


@dataclass_json
@dataclasses.dataclass
class KafkaExporterMetric:
    name: str
    value: float
    timestamp: Optional[int]
    labels: Dict[str, str]


class KafkaBackend:
    """
    Exports metrics as described by https://github.com/ogibayashi/kafka-topic-exporter

    From the docs:

    Each record in the topics should be the following format. timestamp and labels are optional.

    {
      "name": "<metric_name>",
      "value": <metric_value>,
      "timestamp": <epoch_value_with_millis>,
      "labels: {
        "foolabel": "foolabelvalue",
        "barlabel": "barlabelvalue"
      }
    }

    Then the following item will be exported.

    <kafka_topic_name>_<metric_name>{foolabel="foolabelvalue", barlabel="barlabelvalue"} <metric_value> <epoch_value>
    """

    def __init__(self, job_id: str, *, topic: str, bootstrap_servers: List[str] = None, key: str = None):
        self._job_id = job_id
        if bootstrap_servers is None:
            bootstrap_servers = ["localhost:9092"]
        self._producer = create_kafka_producer(bootstrap_servers)
        self._key = key
        self._topic = topic

    def __call__(self, metrics):
        now = datetime.datetime.utcnow()
        # now = datetime.datetime(1970, 1, 1, hour=0, minute=0, second=1)
        # epoch = datetime.datetime(1970, 1, 1)
        # timestamp = int((now - epoch).total_seconds() * 1000)
        timestamp_in_millis = int(now.timestamp()) * 1000
        for metric_name, metric_value in metrics.items():
            metric_object = KafkaExporterMetric(
                name=metric_name,
                value=metric_value,
                timestamp=timestamp_in_millis,
                labels={"job-id": self._job_id, "sender": "metrics-pusher"},
            )

            # TODO: Handle KafkaTimeoutError
            self._producer.send(self._topic, value=metric_object, key=self._key)
