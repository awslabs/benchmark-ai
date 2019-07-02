import logging

__version__ = "0.1.0"
SERVICE_NAME = "watcher"
SERVICE_DESCRIPTION = "Watcher service to monitor benchmark executions and emit their status"

service_logger = logging.getLogger(SERVICE_NAME)
