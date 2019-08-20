ENV_NAME = metrics-pusher

include ../etc/base-common.mk
include ../etc/python-common.mk

PROJECT=metrics-pusher

include ../etc/docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
