import logging


LOGGING_FORMAT = "%(asctime)s %(levelname)s: %(message)s"


def configure_logging(**kwargs):
    logging.basicConfig(format=LOGGING_FORMAT, **kwargs)
