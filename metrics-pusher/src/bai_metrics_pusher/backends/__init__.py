from .elasticsearch_backend import ElasticsearchBackend
from .logging_backend import LoggingBackend


BACKENDS = {"stdout": LoggingBackend, "elasticsearch": ElasticsearchBackend}


def create_backend(backend: str, *args, **kwargs):
    return BACKENDS[backend](*args, **kwargs)
