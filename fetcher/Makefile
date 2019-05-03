ENV_NAME = fetcher

include ../python-common.mk

DOCKER_IMAGE_TAG=stsukrov/fetcher-dispatcher

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt

_docker_package:
	$(DOCKER) build .. -f ../Dockerfile-fetcher -t $(DOCKER_IMAGE_TAG)