ENV_NAME = watcher

include ../etc/base-common.mk
include ../python-common.mk

PROJECT=watcher

include ../docker-common.mk
include ../deploy-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
