DOCKER = docker
DEPLOY_ENV_NAME = deploy-$(ENV_NAME)
DEPLOY_CONDA_RUN = conda run --name $(DEPLOY_ENV_NAME)
KUBECTL = $(DEPLOY_CONDA_RUN) kubectl

BENCHMARK_DIR ?= ..

DOCKERHUB_ORG = benchmarkai
DOCKER_REPOSITORY = $(DOCKERHUB_ORG)/$(PROJECT)

COMMIT_SHORT_HASH := $(shell git rev-parse --short HEAD)
DOCKER_IMAGE_LABEL ?= $(COMMIT_SHORT_HASH)
DOCKER_IMAGE_TAG = $(DOCKER_REPOSITORY):$(DOCKER_IMAGE_LABEL)

# package is a high level command while docker_package can be executed separately
package: build docker_package

_pre_docker_package::
	echo "Pre docker actions"

_docker_package: _pre_docker_package
	$(DOCKER) build . -t $(DOCKER_IMAGE_TAG)

_post_docker_package:: _docker_package
	echo "Post docker actions"

docker_package: _post_docker_package

publish: package docker_publish

docker_publish: docker_package
	echo "Publishing $(DOCKER_IMAGE_TAG)"
	[[ "$(STAGE)" == "local" ]] && echo "Skipping local publishing step - use local docker repo" || $(DOCKER) push $(DOCKER_IMAGE_TAG)

_deploy_venv:
	conda env update --file $(BENCHMARK_DIR)/deploy-environment.yml --prune --name $(DEPLOY_ENV_NAME)

deploy: publish k8s_deploy

undeploy: k8s_undeploy

#---------------------
# K8S deploy/undeploy
#---------------------
define fn_k8s_deploy
	find ./deploy -name '*.yml' -exec sh -c "sed 's|@@DOCKER_IMAGE_TAG@@|$(DOCKER_IMAGE_TAG)|g' {} | $(KUBECTL) apply $(KUBECTL_FLAGS) -f -" \;
endef

define fn_k8s_undeploy
	$(KUBECTL) delete -f ./deploy $(KUBECTL_FLAGS)
endef

k8s_deploy: _deploy_venv
	$(call fn_k8s_deploy)
k8s_undeploy: _deploy_venv
	$(call fn_k8s_undeploy)

TIMEOUT ?= 300s

_wait_for_job:
	$(KUBECTL) wait --for=condition=complete --timeout=$(TIMEOUT) job/$(JOB_NAME) $(KUBECTL_FLAGS)
