import logging

__version__ = "0.1.0"
APP_NAME = "job-status-trigger"
APP_DESCRIPTION = "Executes a command once the specified kubernetes job has reached the specified status"

app_logger = logging.getLogger(APP_NAME)
