ENV_NAME = fetcher

include ../python-common.mk

DOCKER_IMAGE_TAG=stsukrov/fetcher-dispatcher

include ../docker-common.mk

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

_docker_package:
	$(DOCKER) build .. -f ../Dockerfile-fetcher -t $(DOCKER_IMAGE_TAG)

k8s_deploy_mock_infra:
ifeq ($(STAGE),local)
	$(KUBECTL) apply -f ../mock-infra $(KUBECTL_FLAGS)
endif

k8s_undeploy_mock_infra:
ifeq ($(STAGE),local)
	$(KUBECTL) delete -f ../mock-infra $(KUBECTL_FLAGS)
endif

k8s_deploy: k8s_deploy_mock_infra
	../stage_deploy.sh $(STAGE)

k8s_undeploy: k8s_undeploy_mock_infra
	../stage_deploy.sh $(STAGE) delete
