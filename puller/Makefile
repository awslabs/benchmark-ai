ENV_NAME = puller
PROJECT = puller

include ../docker-common.mk

deploy.yml:
	# A dummy file since puller is not a Kubernetes service
	touch deploy.yml

_docker_package: _pre_docker_package
	$(DOCKER) build . -t $(DOCKER_IMAGE_TAG)

override define fn_k8s_deploy
	echo "Skipping Kubernetes deployment"
endef
