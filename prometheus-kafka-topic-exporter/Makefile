ENV_NAME = prometheus-kafka-topic-exporter

PROJECT=prometheus-kafka-topic-exporter

include ../docker-common.mk

STAGE ?= devo

build:

k8s_deploy: _k8_create_configmap

_k8_create_configmap:
	${KUBECTL} create configmap prometheus-kafka-topic-exporter-config --from-file $(BENCHMARK_DIR)/prometheus-kafka-topic-exporter/config/

_docker_package: _pre_docker_package
	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-$(PROJECT) -t $(DOCKER_IMAGE_TAG)
