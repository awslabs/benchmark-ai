ENV_NAME = fetcher

include ../python-common.mk

PROJECT=fetcher-dispatcher

include ../docker-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

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


# HACK: Overriding also package and publish because the sed approach to automatically replace tags is difficult
# to use here due to the Kustomize-ness
_docker_package: _pre_docker_package
	$(DOCKER) build .. -f ../Dockerfile-$(PROJECT) -t $(DOCKER_REPOSITORY):latest

docker_publish: docker_package
	echo "Publishing $(DOCKER_REPOSITORY):latest"
	$(DOCKER) push $(DOCKER_REPOSITORY):latest
