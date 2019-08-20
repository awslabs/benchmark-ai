ENV_NAME = watcher

include ../etc/base-common.mk
include ../etc/python-common.mk

PROJECT=watcher

include ../etc/docker-common.mk
include ../etc/deploy-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
