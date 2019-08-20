ENV_NAME = metrics-extractor

include ../etc/base-common.mk
include ../python-common.mk

PROJECT=metrics-extractor

include ../etc/docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
