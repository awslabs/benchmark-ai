SHELL :=/bin/bash

DOCKER = docker
BENCHMARK_DIR ?= ..

DOCKER_REGISTRY = benchmarkai
DOCKER_REPOSITORY = $(DOCKER_REGISTRY)/$(PROJECT)

COMMIT_SHORT_HASH ?= $(shell git rev-parse --short HEAD)
DOCKER_IMAGE_LABEL ?= $(COMMIT_SHORT_HASH)
DOCKER_IMAGE_TAG = $(DOCKER_REPOSITORY):$(DOCKER_IMAGE_LABEL)

# Default local action - don't push
LOCAL_PUBLISH ?= echo "Skipping local publishing step - use local docker repo"

# package is a high level command while docker_package can be executed separately
package: build docker_package


_pre_docker_package::
	echo "Pre docker actions"

_docker_package: _pre_docker_package
	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/etc/Dockerfile-service --build-arg SERVICE=$(PROJECT) -t $(DOCKER_IMAGE_TAG)

_post_docker_package:: _docker_package
	echo "Post docker actions"

docker_package: _post_docker_package

bootstrap_package::
	$(DOCKER) build -f $(BENCHMARK_DIR)/etc/Dockerfile-dev -t latest .
	$(DOCKER) tag latest ${BOOTSTRAP_DOCKER_URL}

publish: docker_publish

docker_publish: docker_package
	echo "Publishing $(DOCKER_IMAGE_TAG)"
	[[ "$(STAGE)" == "local" ]] && $(LOCAL_PUBLISH) $(DOCKER_IMAGE_TAG) || $(DOCKER) push $(DOCKER_IMAGE_TAG)

bootstrap_publish: bootstrap_package
	docker push ${BOOTSTRAP_DOCKER_URL}
