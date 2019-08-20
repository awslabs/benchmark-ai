ENV_NAME = executor

include ../etc/base-common.mk
include ../etc/python-common.mk

PROJECT=executor

include ../etc/docker-common.mk
include ../etc/deploy-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

PULLER_DOCKER_IMAGE_TAG =  $(DOCKER_REGISTRY)/puller:$(DOCKER_IMAGE_LABEL)
METRICS_PUSHER_DOCKER_IMAGE_TAG =  $(DOCKER_REGISTRY)/metrics-pusher:$(DOCKER_IMAGE_LABEL)
CRON_JOB_DOCKER_IMAGE_TAG =  $(DOCKER_REGISTRY)/cron-job:$(DOCKER_IMAGE_LABEL)

deploy.yml: _deploy_venv
	echo "Kustomize deployment"
	$(DEPLOY_CONDA_RUN) sed -e 's\|@@DOCKER_IMAGE_TAG@@\|$(DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@PULLER_DOCKER_IMAGE_TAG@@\|$(PULLER_DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@METRICS_PUSHER_DOCKER_IMAGE_TAG@@\|$(METRICS_PUSHER_DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@CRON_JOB_DOCKER_IMAGE_TAG@@\|$(CRON_JOB_DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@STAGE@@\|$(STAGE)\|g' deploy/kustomization.tpl.yml > deploy/kustomization.yml
	$(KUBECTL) kustomize deploy > deploy.yml
	rm -f deploy/kustomization.yml

ifeq ($(STAGE),local)
#Pass special label designed for local integration tests
  JOB_DOCKER_IMAGE_LABEL=local-latest
  TEST_LABEL=DOCKER_IMAGE_LABEL=$(JOB_DOCKER_IMAGE_LABEL)
else
  TEST_LABEL=
endif

.PHONY: integration_tests

integration_tests:
	echo $(TEST_LABEL)
	cd $(INTEGRATION_TEST_FOLDERS) && $(MAKE) run $(TEST_LABEL)
