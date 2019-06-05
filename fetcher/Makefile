ENV_NAME = fetcher

include ../python-common.mk

PROJECT=fetcher

include ../docker-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

.PHONY: integration_tests

ifeq ($(STAGE),local)
#Pass special label designed for local integration tests
  TEST_LABEL=DOCKER_IMAGE_LABEL=local-latest
else
  TEST_LABEL=
endif

integration_tests:
	echo $(TEST_LABEL)
	cd mock-fetcher-job && $(MAKE) docker_publish $(TEST_LABEL)
	cd $(INTEGRATION_TEST_FOLDERS) && $(MAKE) run $(TEST_LABEL)

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


# HACK: Overriding also package and publish because the sed approach to automatically replace tags is difficult
# to use here due to the Kustomize-ness
_docker_package: _pre_docker_package
	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-$(PROJECT) -t $(DOCKER_REPOSITORY):latest

docker_publish: docker_package
	echo "Publishing $(DOCKER_REPOSITORY):latest"
	[[ "$(STAGE)" == "local" ]] && echo "Skipping local publishing step - use local docker repo" || $(DOCKER) push $(DOCKER_REPOSITORY):latest

deploy.yml:
	echo "Skipping deploy.yml because deployment is 'Kustomized'"