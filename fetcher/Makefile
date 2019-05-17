ENV_NAME = fetcher

include ../python-common.mk

DOCKER_IMAGE_TAG=stsukrov/fetcher-dispatcher

include ../docker-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

_docker_package:
	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-fetcher -t $(DOCKER_IMAGE_TAG)

.PHONY: integration_tests

integration_tests:
	cd mock-fetcher-job && $(MAKE) docker_publish
	cd $(INTEGRATION_TEST_FOLDERS) && $(MAKE) run

# Overrides how to deploy to Kubernetes because fetcher is using a poor man's version of Kustomize. Until we adopt it
# properly this is good enough.
override define fn_k8s_deploy
	[[ "$(STAGE)" == "local" ]] && $(KUBECTL) apply -f $(BENCHMARK_DIR)/mock-infra $(KUBECTL_FLAGS) || true
	$(DEPLOY_CONDA_RUN) $(BENCHMARK_DIR)/stage_deploy.sh $(STAGE)
endef

override define fn_k8s_undeploy
	[[ "$(STAGE)" == "local" ]] && $(KUBECTL) delete -f $(BENCHMARK_DIR)/mock-infra $(KUBECTL_FLAGS) || true
	$(DEPLOY_CONDA_RUN) $(BENCHMARK_DIR)/stage_deploy.sh $(STAGE) delete
endef


