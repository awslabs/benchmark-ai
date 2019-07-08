ENV_NAME = executor

include ../python-common.mk

PROJECT=executor

include ../docker-common.mk
include ../deploy-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

PULLER_DOCKER_IMAGE_TAG =  $(DOCKER_REGISTRY)/puller:$(DOCKER_IMAGE_LABEL)
METRICS_PUSHER_DOCKER_IMAGE_TAG =  $(DOCKER_REGISTRY)/metrics-pusher:$(DOCKER_IMAGE_LABEL)

deploy.yml: _deploy_venv
	echo "Kustomize deployment"
	$(DEPLOY_CONDA_RUN) sed -e 's\|@@DOCKER_IMAGE_TAG@@\|$(DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@PULLER_DOCKER_IMAGE_TAG@@\|$(PULLER_DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@METRICS_PUSHER_DOCKER_IMAGE_TAG@@\|$(METRICS_PUSHER_DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@STAGE@@\|$(STAGE)\|g' deploy/kustomization.tpl.yml > deploy/kustomization.yml
	$(KUBECTL) kustomize deploy > deploy.yml
	rm -f deploy/kustomization.yml

integration_tests:
	echo "Integration tests will be here"