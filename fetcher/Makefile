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
  DOCKER_IMAGE_LABEL=local-latest
  TEST_LABEL=DOCKER_IMAGE_LABEL=$(DOCKER_IMAGE_LABEL)
  JOB_PROJECT=mock-fetcher-job
else
  TEST_LABEL=
  JOB_PROJECT=fetcher-job
endif

JOB_DOCKER_REPOSITORY = $(DOCKER_REGISTRY)/$(JOB_PROJECT)
JOB_DOCKER_IMAGE_TAG = $(JOB_DOCKER_REPOSITORY):$(DOCKER_IMAGE_LABEL)

integration_tests:
	echo $(TEST_LABEL)
	cd mock-fetcher-job && $(MAKE) docker_publish $(TEST_LABEL)
	cd $(INTEGRATION_TEST_FOLDERS) && $(MAKE) run $(TEST_LABEL)

# Overrides how to deploy to Kubernetes because fetcher is using a poor man's version of Kustomize. Until we adopt it
# properly this is good enough.
override define fn_k8s_deploy
	$(KUBECTL) apply $(KUBECTL_FLAGS) -k ./deploy
endef

override define fn_k8s_undeploy
	$(KUBECTL) delete $(KUBECTL_FLAGS) -k ./deploy
endef

generate_deploy:
	echo "Kustomize deployment"
	$(DEPLOY_CONDA_RUN) sed -e 's\|@@DOCKER_IMAGE_TAG@@\|$(DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@JOB_DOCKER_IMAGE_TAG@@\|$(JOB_DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@STAGE@@\|$(STAGE)\|g' deploy/kustomization.tpl.yml > deploy/kustomization.yml
