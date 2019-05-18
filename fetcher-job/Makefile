ENV_NAME = fetcher-job

include ../python-common.mk

PROJECT=fetcher-job

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt

_docker_package: _pre_docker_package
	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-$(PROJECT) -t $(DOCKER_IMAGE_TAG)

