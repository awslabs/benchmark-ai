DOCKER = docker
KUBECTL = kubectl

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

deploy: publish k8s_deploy

k8s_deploy: docker_publish
	$(KUBECTL) apply -f ./deploy $(KUBECTL_FLAGS)
