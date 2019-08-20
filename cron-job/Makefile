ENV_NAME = cron-job

include ../etc/base-common.mk
include ../etc/python-common.mk

PROJECT=cron-job

include ../etc/docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
