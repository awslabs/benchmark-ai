ENV_NAME = fetcher

include ../etc/base-common.mk
include ../python-common.mk

PROJECT=fetcher

include ../docker-common.mk
include ../deploy-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

.PHONY: integration_tests

ifeq ($(STAGE),local)
#Pass special label designed for local integration tests
  JOB_DOCKER_IMAGE_LABEL=local-latest
  TEST_LABEL=DOCKER_IMAGE_LABEL=$(JOB_DOCKER_IMAGE_LABEL)
  JOB_PROJECT=mock-fetcher-job
else
  JOB_DOCKER_IMAGE_LABEL=$(DOCKER_IMAGE_LABEL)
  TEST_LABEL=
  JOB_PROJECT=fetcher-job
endif

JOB_DOCKER_REPOSITORY = $(DOCKER_REGISTRY)/$(JOB_PROJECT)
JOB_DOCKER_IMAGE_TAG = $(JOB_DOCKER_REPOSITORY):$(JOB_DOCKER_IMAGE_LABEL)

integration_tests:
	echo $(TEST_LABEL)
	cd mock-fetcher-job && $(MAKE) docker_publish $(TEST_LABEL)
	cd $(INTEGRATION_TEST_FOLDERS) && $(MAKE) run $(TEST_LABEL)

deploy.yml: _deploy_venv
	echo "Kustomize deployment"
	$(DEPLOY_CONDA_RUN) sed -e 's\|@@DOCKER_IMAGE_TAG@@\|$(DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@JOB_DOCKER_IMAGE_TAG@@\|$(JOB_DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@STAGE@@\|$(STAGE)\|g' deploy/kustomization.tpl.yml > deploy/kustomization.yml
	$(KUBECTL) kustomize deploy > deploy.yml
	rm -f deploy/kustomization.yml
