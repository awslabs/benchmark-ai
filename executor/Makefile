ENV_NAME = executor

include ../python-common.mk

DOCKER_IMAGE_TAG=jlcont/baiexecutor

include ../docker-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

_docker_package:
	$(DOCKER) build .. -f ../Dockerfile-executor -t $(DOCKER_IMAGE_TAG)
