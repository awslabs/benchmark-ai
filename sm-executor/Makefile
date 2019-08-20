ENV_NAME = sm-executor

include ../etc/base-common.mk
include ../python-common.mk

PROJECT = sm-executor

include ../docker-common.mk
include ../etc/deploy-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

deploy.yml: _deploy_venv
	echo "Kustomize deployment"
	$(DEPLOY_CONDA_RUN) sed -e 's\|@@DOCKER_IMAGE_TAG@@\|$(DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@STAGE@@\|$(STAGE)\|g' deploy/kustomization.tpl.yml > deploy/kustomization.yml
	$(KUBECTL) kustomize deploy > deploy.yml
	rm -f deploy/kustomization.yml
