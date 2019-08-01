ENV_NAME = anubis-cron-job

include ../base-common.mk
include ../python-common.mk

PROJECT=cron-job

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
