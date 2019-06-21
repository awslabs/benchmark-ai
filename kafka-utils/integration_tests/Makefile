PROJECT = kafka-utils-it
ENV_NAME = kafka-utils-test
SERVICE = kafka-utils
BENCHMARK_DIR = ../..

include $(BENCHMARK_DIR)/python-common.mk

JOB_NAME = kafka-utils-it

include $(BENCHMARK_DIR)/docker-common.mk


build:
	echo "Stub target for build"

run: clean publish k8s_run

k8s_run: _k8s_silent_undeploy k8s_deploy _wait_for_job clean_kustomization


_docker_package: _pre_docker_package
	$(DOCKER) build --no-cache $(BENCHMARK_DIR) -f $(BENCHMARK_DIR)/Dockerfile-it --build-arg SERVICE=$(SERVICE) -t $(DOCKER_IMAGE_TAG)


# Copy pasted from fetcher
override define fn_k8s_deploy
	$(KUBECTL) apply -k ./deploy/$(STAGE) $(KUBECTL_FLAGS)
endef

override define fn_k8s_undeploy
	$(KUBECTL) delete -k ./deploy/$(STAGE) $(KUBECTL_FLAGS)
endef

_k8s_silent_undeploy:
	-$(KUBECTL) delete -k ./deploy/$(STAGE) $(KUBECTL_FLAGS)

deploy.yml:
	echo "Kustomize deployment"
	sed -e 's|@@DOCKER_IMAGE_TAG@@|$(DOCKER_IMAGE_TAG)|g' \
		-e 's|@@STAGE@@|$(STAGE)|g' deploy/kustomization.tpl.yml > deploy/kustomization.yml

clean_kustomization:
	rm deploy/kustomization.yml

