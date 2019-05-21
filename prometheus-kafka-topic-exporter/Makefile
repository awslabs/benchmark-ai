ENV_NAME = prometheus-kafka-topic-exporter

include ../python-common.mk

PROJECT=executor

include ../docker-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt
