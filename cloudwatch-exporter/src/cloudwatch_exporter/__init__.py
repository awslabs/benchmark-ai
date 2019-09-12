import logging

__version__ = "1.0"
SERVICE_NAME = "cloudwatch-exporter"
SERVICE_DESCRIPTION = "Service to listen to metrics events and post them to CloudWatch"

service_logger = logging.getLogger(SERVICE_NAME)
