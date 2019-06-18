ENV_NAME = kafka-utils-test

include ../python-common.mk

publish:
	echo "Nothing to publish"

# Copy paste from fetcher
PROJECT=kafka-utils

include ../docker-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

.PHONY: integration_tests

ifeq ($(STAGE),local)
#Pass special label designed for local integration tests
  DOCKER_IMAGE_LABEL=local-latest
  TEST_LABEL=DOCKER_IMAGE_LABEL=$(DOCKER_IMAGE_LABEL)
else
  TEST_LABEL=
endif

JOB_DOCKER_REPOSITORY = $(DOCKER_REGISTRY)/$(JOB_PROJECT)
JOB_DOCKER_IMAGE_TAG = $(JOB_DOCKER_REPOSITORY):$(DOCKER_IMAGE_LABEL)

integration_tests:
	echo $(TEST_LABEL)
	cd $(INTEGRATION_TEST_FOLDERS) && $(MAKE) run $(TEST_LABEL)

#override define fn_k8s_deploy
#	$(KUBECTL) apply $(KUBECTL_FLAGS) -k ./deploy
#endef
#
#override define fn_k8s_undeploy
#	$(KUBECTL) delete $(KUBECTL_FLAGS) -k ./deploy
#endef
#
#deploy.yml:
#	echo "Kustomize deployment"
#	sed -e 's|@@DOCKER_IMAGE_TAG@@|$(DOCKER_IMAGE_TAG)|g' \
#		-e 's|@@STAGE@@|$(STAGE)|g' deploy/kustomization.tpl.yml > deploy/kustomization.yml
