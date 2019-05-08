ENV_NAME = fetcher

include ../python-common.mk

PROJECT=fetcher-dispatcher

include ../docker-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

_docker_package:
	$(DOCKER) build .. -f ../Dockerfile-fetcher -t $(DOCKER_IMAGE_TAG)

# Overrides how to deploy to Kubernetes because fetcher is using a poor man's version of Kustomize. Until we adopt it
# properly this is good enough.
override define fn_k8s_deploy
	[[ "$(STAGE)" == "local" ]] && $(KUBECTL) apply -f ../mock-infra $(KUBECTL_FLAGS) || true
	$(DEPLOY_CONDA_RUN) ../stage_deploy.sh $(STAGE)
endef

override define fn_k8s_undeploy
	[[ "$(STAGE)" == "local" ]] && $(KUBECTL) delete -f ../mock-infra $(KUBECTL_FLAGS) || true
	$(DEPLOY_CONDA_RUN) ../stage_deploy.sh $(STAGE) delete
endef
