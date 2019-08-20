ENV_NAME=prometheus-kafka-topic-exporter

PROJECT=prometheus-kafka-topic-exporter

include ../etc/base-common.mk
include ../docker-common.mk
include ../deploy-common.mk

STAGE ?= devo

.DEFAULT_GOAL := default

default: build

build:
	echo "Nothing to build"

override define fn_k8s_deploy
	$(KUBECTL) apply $(KUBECTL_FLAGS) -f deploy.yml
	# https://github.com/kubernetes/kubernetes/issues/25832#issuecomment-220445845
	${KUBECTL} create configmap prometheus-kafka-topic-exporter-config --from-file $(BENCHMARK_DIR)/prometheus-kafka-topic-exporter/config/ --dry-run -o yaml | ${KUBECTL} apply -f -
endef

_docker_package: _pre_docker_package
	$(DOCKER) build . -t $(DOCKER_IMAGE_TAG)
