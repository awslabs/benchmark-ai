DOCKER = docker
DEPLOY_ENV_NAME = deploy-$(ENV_NAME)
DEPLOY_CONDA_RUN = conda run --name $(DEPLOY_ENV_NAME)
KUBECTL = $(DEPLOY_CONDA_RUN) kubectl

#package is a high level commandm while docker_package can be executed separately
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
	$(DOCKER) push $(DOCKER_IMAGE_TAG)

_deploy_venv:
	conda env update --file ../deploy-environment.yml --prune --name $(DEPLOY_ENV_NAME)


deploy: publish k8s_deploy

undeploy: k8s_undeploy

k8s_deploy: _deploy_venv _k8s_deploy
_k8s_deploy:
	$(KUBECTL) apply -f ./deploy $(KUBECTL_FLAGS)

k8s_undeploy: _deploy_venv _k8s_undeploy
_k8s_undeploy:
	$(KUBECTL) delete -f ./deploy $(KUBECTL_FLAGS)
