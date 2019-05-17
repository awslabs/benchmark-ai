ENV_NAME = metrics-pusher

include ../python-common.mk

PROJECT=metrics-pusher

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
