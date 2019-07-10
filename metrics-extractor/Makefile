ENV_NAME = metrics-extractor

include ../base-common.mk
include ../python-common.mk

PROJECT=metrics-extractor

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
