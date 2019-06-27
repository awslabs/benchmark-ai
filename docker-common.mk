SHELL :=/bin/bash

DOCKER = docker
DEPLOY_ENV_NAME = deploy-$(ENV_NAME)
DEPLOY_CONDA_RUN = conda run --name $(DEPLOY_ENV_NAME)
DEPLOY_CONDA_RUN_SHELL = $(DEPLOY_CONDA_RUN) $(SHELL)
# Employ conda run as soon as kubectl 1.14 is available
KUBECTL = kubectl

BENCHMARK_DIR ?= ..

DOCKER_REGISTRY = benchmarkai
DOCKER_REPOSITORY = $(DOCKER_REGISTRY)/$(PROJECT)

COMMIT_SHORT_HASH ?= $(shell git rev-parse --short HEAD)
DOCKER_IMAGE_LABEL ?= $(COMMIT_SHORT_HASH)
DOCKER_IMAGE_TAG = $(DOCKER_REPOSITORY):$(DOCKER_IMAGE_LABEL)

# Default local action - don't push
LOCAL_DEPLOY = echo "Skipping local publishing step - use local docker repo"

CACHE_LAYERS=false

# package is a high level command while docker_package can be executed separately
package: build docker_package

_pre_docker_package::
	echo "Pre docker actions"

_docker_package: _pre_docker_package
ifeq ($(CACHE_LAYERS),true)
	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-service --build-arg SERVICE=$(PROJECT) --target=base -t $(DOCKER_REPOSITORY):base-ci-latest --cache-from=$(DOCKER_REPOSITORY):base-ci-latest
	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-service --build-arg SERVICE=$(PROJECT) -t $(DOCKER_REPOSITORY):base-ci-latest --cache-from=$(DOCKER_REPOSITORY):ci-latest
endif

	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-service --build-arg SERVICE=$(PROJECT) -t $(DOCKER_IMAGE_TAG)

ifeq ($(CACHE_LAYERS),true)
	$(DOCKER) push $(BENCHMARK_DIR) $(DOCKER_REPOSITORY):base-ci-latest
	$(DOCKER) push $(BENCHMARK_DIR) $(DOCKER_REPOSITORY):ci-latest
endif


_post_docker_package:: _docker_package
	echo "Post docker actions"

docker_package: _post_docker_package

publish: docker_publish

docker_publish: docker_package
	echo "Publishing $(DOCKER_IMAGE_TAG)"
	[[ "$(STAGE)" == "local" ]] && $(LOCAL_DEPLOY) $(DOCKER_IMAGE_TAG) || $(DOCKER) push $(DOCKER_IMAGE_TAG)

_deploy_venv:
	conda env update --file $(BENCHMARK_DIR)/deploy-environment.yml --prune --name $(DEPLOY_ENV_NAME)

deploy: publish k8s_deploy

undeploy: k8s_undeploy

#---------------------
# K8S deploy/undeploy
#---------------------
define fn_k8s_deploy
	$(KUBECTL) apply $(KUBECTL_FLAGS) -f deploy.yml
endef

deploy.yml: _deploy_venv
	rm -f deploy.yml
	cd deploy && for file in *.yml ; do \
		[ -f $${file} ] && $(DEPLOY_CONDA_RUN) sed -e 's\|@@DOCKER_IMAGE_TAG@@\|$(DOCKER_IMAGE_TAG)\|g' $${file} >> ../deploy.yml && echo "---" >> ../deploy.yml ; \
	done

define fn_k8s_undeploy
	$(KUBECTL) delete -f ./deploy $(KUBECTL_FLAGS)
endef

k8s_deploy: deploy.yml
	$(call fn_k8s_deploy)
k8s_undeploy: _deploy_venv
	$(call fn_k8s_undeploy)

JOB_TIMEOUT ?= 300

_wait_for_job:
	$(SHELL) $(BENCHMARK_DIR)/wait_for_job.sh $(JOB_NAME) $(JOB_TIMEOUT)
