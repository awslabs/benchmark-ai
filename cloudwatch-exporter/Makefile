ENV_NAME = cloudwatch-exporter

include ../etc/base-common.mk
include ../etc/python-common.mk

PROJECT=cloudwatch-exporter

include ../etc/docker-common.mk
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

ifeq ($(STAGE),local)
#Pass special label designed for local integration tests
  JOB_DOCKER_IMAGE_LABEL=local-latest
  TEST_LABEL=DOCKER_IMAGE_LABEL=$(JOB_DOCKER_IMAGE_LABEL)
else
  TEST_LABEL=
endif
