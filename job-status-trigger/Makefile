ENV_NAME = job-status-trigger

include ../etc/base-common.mk
include ../etc/python-common.mk

PROJECT=job-status-trigger

include ../etc/docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
