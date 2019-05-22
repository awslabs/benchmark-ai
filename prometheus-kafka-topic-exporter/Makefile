ENV_NAME = prometheus-kafka-topic-exporter

PROJECT=prometheus-kafka-topic-exporter

include ../docker-common.mk

STAGE ?= devo

build:


_post_venv::
	$(PIP) install -r requirements.txt

_docker_package: _pre_docker_package
	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-$(PROJECT) -t $(DOCKER_IMAGE_TAG)
