ENV_NAME = watcher

include ../base-common.mk
include ../python-common.mk

PROJECT=watcher

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
