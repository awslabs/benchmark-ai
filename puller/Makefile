ENV_NAME = puller
PROJECT = puller

include ../etc/base-common.mk
include ../etc/docker-common.mk

_docker_package: _pre_docker_package
	$(DOCKER) build . -t $(DOCKER_IMAGE_TAG)
