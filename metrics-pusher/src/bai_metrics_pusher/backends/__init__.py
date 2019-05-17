from bai_metrics_pusher.backends.kafka_backend import KafkaBackend
from .elasticsearch_backend import ElasticsearchBackend
from .logging_backend import LoggingBackend


BACKENDS = {"stdout": LoggingBackend, "elasticsearch": ElasticsearchBackend, "kafka": KafkaBackend}


def create_backend(backend: str, *args, **kwargs):
    return BACKENDS[backend](*args, **kwargs)
