# Include this file to be able to deploy Kubernetes yaml files.
# It requires that `docker-common.mk` was included before.

_deploy_venv:
	conda env update --file $(BENCHMARK_DIR)/deploy-environment.yml --prune --name $(DEPLOY_ENV_NAME)

deploy: deploy.yml _deploy_venv
	$(call fn_k8s_deploy)

undeploy: deploy.yml _deploy_venv
	$(call fn_k8s_undeploy)

#---------------------
# K8S deploy/undeploy
#---------------------
define fn_k8s_deploy
	$(KUBECTL) apply $(KUBECTL_FLAGS) -f deploy.yml
endef

define fn_k8s_undeploy
	$(KUBECTL) delete $(KUBECTL_FLAGS) -f deploy.yml
endef

.PHONY: deploy.yml
.PHONY: deploy
.PHONY: undeploy

deploy.yml: _deploy_venv
	rm -f deploy.yml
	cd deploy && for file in *.yml ; do \
		[ -f $${file} ] && $(DEPLOY_CONDA_RUN) sed -e 's\|@@DOCKER_IMAGE_TAG@@\|$(DOCKER_IMAGE_TAG)\|g' $${file} >> ../deploy.yml && echo "---" >> ../deploy.yml ; \
	done

JOB_TIMEOUT ?= 300

_wait_for_job:
	$(SHELL) $(BENCHMARK_DIR)/wait_for_job.sh $(JOB_NAME) $(JOB_TIMEOUT)