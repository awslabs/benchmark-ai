ENV_NAME = inference-benchmark

include ../etc/base-common.mk
include ../etc/python-common.mk

PROJECT=inference-benchmark

include ../etc/docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt
