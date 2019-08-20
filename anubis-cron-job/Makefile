ENV_NAME = anubis-cron-job

include ../etc/base-common.mk
include ../python-common.mk

PROJECT=anubis-cron-job

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
