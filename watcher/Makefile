ENV_NAME = watcher

include ../python-common.mk

DOCKER_IMAGE_TAG=edisongustavo/bai-watcher

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt

_docker_package:
	$(DOCKER) build .. -f ../Dockerfile-watcher -t $(DOCKER_IMAGE_TAG)