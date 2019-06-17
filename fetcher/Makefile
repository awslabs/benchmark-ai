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
	$(KUBECTL) apply $(KUBECTL_FLAGS) -k ./deploy
endef

override define fn_k8s_undeploy
	$(KUBECTL) delete $(KUBECTL_FLAGS) -k ./deploy
endef

deploy.yml: deploy/kustomization.yml
	echo "Kustomize deployment"

deploy/kustomization.yml:
	echo "Generating deploy/kustomization.yml"
	sed -e 's|@@DOCKER_IMAGE_LABEL@@|$(DOCKER_IMAGE_LABEL)|g' -e 's|@@STAGE@@|$(STAGE)|g' deploy/kustomization.yml.tmpl > deploy/kustomization.yml
