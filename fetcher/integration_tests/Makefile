PROJECT = fetcher-it
ENV_NAME = fetcherit

BENCHMARK_DIR=../..

JOB_NAME=fetcher-it

include $(BENCHMARK_DIR)/docker-common.mk


build:
	echo "Stub target for build"

run: publish k8s_run

k8s_run: _k8s_silent_cleanup _k8s_silent_undeploy k8s_deploy _wait_for_job _k8s_cleanup

#Copy paste from the fetcher
override define fn_k8s_deploy
	$(DEPLOY_CONDA_RUN) $(BENCHMARK_DIR)/stage_deploy.sh $(STAGE)
endef

override define fn_k8s_undeploy
	$(DEPLOY_CONDA_RUN) $(BENCHMARK_DIR)/stage_deploy.sh $(STAGE) delete
endef

_k8s_silent_undeploy:
	-$(DEPLOY_CONDA_RUN) $(BENCHMARK_DIR)/stage_deploy.sh $(STAGE) delete

_k8s_cleanup:
	$(KUBECTL) delete jobs --selector action-id $(KUBECTL_FLAGS)

_k8s_silent_cleanup:
	-$(KUBECTL) delete jobs --selector action-id $(KUBECTL_FLAGS)









