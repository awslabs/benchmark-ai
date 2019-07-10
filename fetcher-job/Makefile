ENV_NAME = fetcher-job

include ../base-common.mk
include ../python-common.mk

PROJECT=fetcher-job

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
