ENV_NAME = fetcher-job

include ../etc/base-common.mk
include ../python-common.mk

PROJECT=fetcher-job

include ../etc/docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
