PROJECT = mock-fetcher-job

BENCHMARK_DIR = ../..

include $(BENCHMARK_DIR)/etc/docker-common.mk

build:
	echo "Stub target for build"

_docker_package: _pre_docker_package
	$(DOCKER) build . -t $(DOCKER_IMAGE_TAG)
