PROJECT = executor-it
SERVICE = executor
ENV_NAME = executorit

BENCHMARK_DIR=../..

JOB_NAME=executor-it
STAGE ?= devo

include $(BENCHMARK_DIR)/docker-common.mk
include $(BENCHMARK_DIR)/deploy-common.mk


build:
	echo "Stub target for build"

run: publish k8s_run

k8s_run: _k8s_silent_cleanup _k8s_silent_undeploy deploy _wait_for_job _k8s_cleanup

_docker_package: _pre_docker_package
	$(DOCKER) build $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-it --build-arg SERVICE=$(SERVICE) -t $(DOCKER_IMAGE_TAG)


#Copy paste from the executor

_k8s_silent_undeploy:
	-$(KUBECTL) delete -k ./deploy/$(STAGE) $(KUBECTL_FLAGS)

_k8s_cleanup:
	$(KUBECTL) delete jobs,persistentvolumeclaims --selector action-id $(KUBECTL_FLAGS)

_k8s_silent_cleanup:
	-$(KUBECTL) delete jobs,persistentvolumeclaims --selector action-id $(KUBECTL_FLAGS)

deploy.yml:
	# $(KUBECTL) kustomize ./deploy/$(STAGE) > deploy.yml
	echo "Kustomize deployment"
	$(DEPLOY_CONDA_RUN) sed -e 's\|@@DOCKER_IMAGE_TAG@@\|$(DOCKER_IMAGE_TAG)\|g' \
		-e 's\|@@STAGE@@\|$(STAGE)\|g' deploy/kustomization.tpl.yml > deploy/kustomization.yml
	cat deploy/kustomization.yml
	$(KUBECTL) kustomize deploy > deploy.yml
	rm -f deploy/kustomization.yml
