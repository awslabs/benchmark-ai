ENV_NAME = prometheus-kafka-topic-exporter

PROJECT=prometheus-kafka-topic-exporter

include ../docker-common.mk

STAGE ?= devo

build:

k8s_deploy: _k8_create_configmap

_k8_create_configmap:
	# https://github.com/kubernetes/kubernetes/issues/25832#issuecomment-220445845
	${KUBECTL} create configmap prometheus-kafka-topic-exporter-config --from-file $(BENCHMARK_DIR)/prometheus-kafka-topic-exporter/config/ --dry-run -o yaml | ${KUBECTL} replace configmap prometheus-kafka-topic-exporter-config -f -

_docker_package: _pre_docker_package
	$(DOCKER) build . -t $(DOCKER_IMAGE_TAG)

