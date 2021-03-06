#NOTE: Requires: sed, git, docker, kubectl
SHELL :=/bin/bash

.DEFAULT_GOAL := build

ENV_NAME = bff
ifneq (, $(shell which conda))
# If doing `deploy`, then we use conda to grab the dependencies
include ../etc/base-common.mk
include ../etc/deploy-common.mk
CONDA_DEPLOY_ENV_BIN = $(CONDA_ROOT)/envs/$(DEPLOY_ENV_NAME)/bin
export PATH := $(CONDA_DEPLOY_ENV_BIN):$(PATH)
else
_deploy_venv:
	@echo "No conda, so no environment for you :)"
endif

#----------------------------------------------------------------
# Project Specific Info
#----------------------------------------------------------------
PROJECT := bai-bff
ORGANIZATION := MXNet Berlin
RELEASE_NAME := flatbush
PROFILE := prod
AUTHOR := Gavin M. Bell
REPO_SITE = https://github.com/awslabs/benchmark-ai/$(PROJECT)

RESOURCE_PATHS := resources
SOURCE_PATHS := src
TEST_PATHS := test
BIN_PATH := bin

#Created file structures...
COMPILE_PATH := target/classes
TARGET_PATH := target
RELEASE_PATH := release
GEN_DOCS_PATH := docs-generated

#---
# Project metadata info
#---
VCS_PROG := git
#(note: may set VERSION variable in above stanza to override the default below, which gets it from the nearest git tag of the form v.#.#.#<blah>)
VERSION ?= $(shell $(VCS_PROG) tag | sed -n -e 's/^$(PROJECT).*-v\([0-9]*\.[0-9]*\.[0-9]*\).*/\1/p' | sort -s -u -t. -k1,1n -k2,2n -k3,3n | tail -n 1)
COMMIT_SHORT_HASH := $(shell $(VCS_PROG) rev-parse --short HEAD)
#TAG := $(PROJECT)-v$(VERSION)-$(shell $(VCS_PROG) rev-list $(PROJECT)-v$(VERSION)..HEAD --count)-g$(COMMIT_SHORT_HASH)
TAG := $(VERSION)-$(COMMIT_SHORT_HASH)
CHANGE_CAUSE := $(shell $(VCS_PROG) log -n1 --pretty=short | xargs | sed -n -e 's/.*>.[ ]*\(.*\)/\1/p')
BRANCH := $(shell $(VCS_PROG) branch | grep '*' | sed -n 's/\*[ ]*//p' | xargs)
COMMIT := $(shell $(VCS_PROG) log -n1 | sed -n -e 's/^commit \(.*\)/\1/p'   | xargs)
COMMIT_DATE :=   $(shell $(VCS_PROG) log -n1 | sed -n -e 's/^Date: \(.*\)/\1/p'   | xargs)
COMMIT_AUTHOR := $(shell $(VCS_PROG) log -n1 | sed -n -e 's/^Author: \(.*\)/\1/p' | xargs)
BUILD_DATE := $(shell date)

#---
# Building core artifact(s)' info
#---
TEMPLATE := etc/project.clj.tmpl
MAIN := $(PROJECT).app
LEIN_ROOT := true
LEIN := ./bin/lein

JMX_PORT=9010
JAR_FILENAME := $(PROJECT)-$(VERSION)-standalone.jar
JAR_FILE := $(TARGET_PATH)/$(JAR_FILENAME)
TARGET := $(PROJECT)-$(VERSION)   #<- (TODO - don't seem to be used)
RELEASE_FILE := $(TARGET).tar.gz  #<- (TODO - don't seem to be used)
CLJ_FILES := $(shell find $(SOURCE_PATHS) -name '*.clj')
CLJ_TEST_FILES := $(shell find $(TEST_PATHS) -name '*.clj')
MAIN_CLASS_FILE := $(COMPILE_PATH)/$(shell sed -e 's@\.@/@g' -e 's@-@_@g' <<<$(MAIN))__init.class
RUN_SCRIPT_NAME := runit
RUN_SCRIPT := $(BIN_PATH)/$(RUN_SCRIPT_NAME)

#---
# Continuous Delivery, Packaging and Containerization
#---
DOCKER_REGISTRY := benchmarkai
DOCKER_TAG := $(VERSION)-$(COMMIT_SHORT_HASH)

CD_SERVER := http://foo.bar.com/job/$(PROJECT)
CD_PACKAGE_VERSION_STAMP := FIXME
CD_RUNTIME_STACK := clojure
CD_MANIFEST := manifest.json
CD_TARGET_PATH := target

#---
# Deployment
#---
DEPLOY_TEMPLATE := etc/deploy.yml.tmpl
DEPLOY_YML := deploy.yml
SERVICE_TEMPLATE := etc/service.yml.tmpl
SERVICE_YML := service.yml
DOCKER_TEMPLATE := etc/Dockerfile.tmpl
DOCKER_DEV_TEMPLATE := etc/Dockerfile-dev.tmpl
SERVICE_ENDPOINT := ./service_endpoint

#Run Environment (ref: deploy template and runit script)
#                (log levels -> #{trace debug info warn error fatal report})
ENVIRONMENT := test
LOGGING_LEVEL := trace
SVC_PORT := 8080
THREAD_POOL_SIZE := 6
MAX_QUEUE_SIZE := 21
#KAFKA_BOOTSTRAP_SERVERS #Here only as a note: gotten from k8s configmap
KAFKA_CONSUMER_GROUP_ID := $(PROJECT)
KAFKA_POLL_INTERVAL_MS := 500
KAFKA_SOURCE_TOPICS := BAI_APP_STATUS,CMD_RETURN
KAFKA_SINK_TOPICS := BAI_APP_STATUS,BAI_APP_BFF,CMD_SUBMIT
KAFKA_DEFAULT_NUM_PARTITIONS := 3
KAFKA_DEFAULT_REPLICATION_FACTOR := 3
#SCRIPTS_EXCHANGE_S3_BUCKET_NAME #Here only as note: gotten from k8s configmap

#This project may be built in the context of a docker environment using the image: gavin/bai-bff-dev
#docker run -it --rm -v "$PWD":/srv/app -w /srv/app gavin/bai-bff-dev <command>

#HACK!!!!
K8S_KUBECTL_ARGS := --kubeconfig=${KUBECONFIG} #--kubeconfig=/Users/bellgav/.devo/kubeconfig
#----------------------------------------------------------------
# The pipeline: clean-all -> [build -> test] -> [package -> publish] -> deploy
#----------------------------------------------------------------

compile: $(MAIN_CLASS_FILE)

$(MAIN_CLASS_FILE): project.clj $(CLJ_FILES)
	$(shell chmod 755 $(LEIN))
	$(LEIN) compile
	@touch $@

build: compile
test: unit-test integration-test docs
package: build-deploy-container
publish: publish-deploy-container

all: build test package #publish #deploy

show-vars:
	@echo "----------------------------------"
	@echo "VERSION =  $(VERSION)"
	@echo "PROJECT = $(PROJECT)"
	@echo "ORGANIZATION = $(ORGANIZATION)"
	@echo "RELEASE_NAME = $(RELEASE_NAME)"
	@echo "PROFILE = $(PROFILE)"
	@echo "AUTHOR = $(AUTHOR)"
	@echo "RESOURCE_PATHS = $(RESOURCE_PATHS)"
	@echo "SOURCE_PATHS = $(SOURCE_PATHS)"
	@echo "TEST_PATHS = $(TEST_PATHS)"
	@echo "BIN_PATH := $(BIN_PATH)"
	@echo "COMPILE_PATH = $(COMPILE_PATH)"
	@echo "TARGET_PATH = $(TARGET_PATH)"
	@echo "RELEASE_PATH = $(RELEASE_PATH)"
	@echo "MAIN = $(MAIN)"
	@echo "----------------------------------"
	@echo "BUILD_DATE = $(BUILD_DATE)"
	@echo "REPO_SITE  = $(REPO_SITE)"
	@echo "BRANCH = $(BRANCH)"
	@echo "TAG    = $(TAG)"
	@echo "CHANGE_CAUSE = $(CHANGE_CAUSE)"
	@echo "COMMIT = $(COMMIT)"
	@echo "COMMIT_AUTHOR = $(COMMIT_AUTHOR)"
	@echo "COMMIT_DATE   = $(COMMIT_DATE)"
	@echo "----------------------------------"
	@echo "DOCKER_REGISTRY : $(DOCKER_REGISTRY)"
	@echo "DOCKER_TAG      : $(DOCKER_TAG)"
	@echo "Package Version : $(CD_PACKAGE_VERSION_STAMP)"
	@echo "----------------------------------"
	$(shell touch $(TEMPLATE))

#-------
# Generates clojure's project.clj file from a template file
# Here (https://github.com/technomancy/leiningen/blob/master/sample.project.clj)
# is the full project.clj file with all the default values explicitly set
#-------
project.clj: $(TEMPLATE)
	@echo "Generating project.clj from template..."
	@sed -e 's|@@AUTHOR@@|$(AUTHOR)|g' \
	     -e 's|@@REPO_SITE@@|$(REPO_SITE)|g' \
	     -e 's|@@PROJECT@@|$(PROJECT)|g' \
             -e 's|@@ORGANIZATION@@|$(ORGANIZATION)|g' \
	     -e 's|@@TAG@@|$(TAG)|g' \
	     -e 's|@@VERSION@@|$(VERSION)|g' \
	     -e 's|@@CD_PACKAGE_VERSION_STAMP@@|$(CD_PACKAGE_VERSION_STAMP)|g' \
	     -e 's|@@BRANCH@@|$(BRANCH)|g' \
	     -e 's|@@COMMIT@@|$(COMMIT)|g' \
	     -e 's|@@COMMIT_AUTHOR@@|$(COMMIT_AUTHOR)|g' \
	     -e 's|@@COMMIT_DATE@@|$(COMMIT_DATE)|g' \
	     -e 's|@@RESOURCE_PATHS@@|$(RESOURCE_PATHS)|g' \
	     -e 's|@@SOURCE_PATHS@@|$(SOURCE_PATHS)|g' \
	     -e 's|@@TEST_PATHS@@|$(TEST_PATHS)|g' \
	     -e 's|@@COMPILE_PATH@@|$(COMPILE_PATH)|g' \
	     -e 's|@@TARGET_PATH@@|$(TARGET_PATH)|g' \
	     -e 's|@@GEN_DOCS_PATH@@|$(GEN_DOCS_PATH)|g' \
	     -e 's|@@MAIN@@|$(MAIN)|g' \
	     -e 's|@@BUILD_DATE@@|$(BUILD_DATE)|g' \
	     -e 's|@@PROFILE@@|$(PROFILE)|g' \
	     -e 's|@@RELEASE_NAME@@|$(RELEASE_NAME)|g' $(TEMPLATE) > $(shell sed -n 's|.*/\(.*\).tmpl|\1|p' <<< $(TEMPLATE))

#NOTE: hardcoded "dist" used instead of TARGET_PATH
#(hesitant to use var here as don't want it overwritten to be "/" or something)
clean:	project.clj
	@$(LEIN) clean
	$(shell [[ -d $(TARGET_PATH) ]] && rm -rf $(TARGET_PATH))

clean-all: clean
	$(shell [[ -f project.clj ]]       && rm project.clj)
	$(shell [[ -f deploy.yml ]]        && rm deploy.yml)
	$(shell [[ -f service.yml ]]       && rm service.yml)
	$(shell [[ -f Dockerfile ]]        && rm Dockerfile)
	$(shell [[ -f Dockerfile-dev ]]    && rm Dockerfile-dev)
	$(shell [[ -d $(RELEASE_PATH) ]]   && rm -rf $(RELEASE_PATH))
	$(shell [[ -d $(COMPILE_PATH) ]]   && rm -rf $(COMPILE_PATH))
	$(shell [[ -d $(GEN_DOCS_PATH) ]]  && rm -rf $(GEN_DOCS_PATH))
	$(shell [[ -d $(CD_TARGET_PATH) ]] && rm -rf $(CD_TARGET_PATH))
	$(shell [[ -f service_endpoint ]]  && rm service_endpoint)


$(JAR_FILE): $(MAIN_CLASS_FILE)
	@echo "------------------------"
	@echo "Building Jar"
	@echo "------------------------"
	@cp -v bin/anubis ${RESOURCE_PATHS}
	LEIN_SNAPSHOTS_IN_RELEASE=1 ${LEIN} with-profile $(PROFILE) uberjar
	@rm -v ${RESOURCE_PATHS}/anubis
	@echo "------------------------"
	@unzip -q -c $(JAR_FILE) META-INF/MANIFEST.MF
	@touch $@


dist:	$(JAR_FILE)

run:	compile
	$(LEIN) run server

docs:	compile
	$(LEIN) codox
	$(LEIN) cloverage
	$(LEIN) vanity

#----------------------------
# Testing...
#----------------------------

unit-test: compile
	@echo "------------------------"
	@echo "Runnig Unit Tests..."
	@echo "------------------------"
	@echo "<not>"

integration-test: compile
	@echo "------------------------"
	@echo "Running Integration Tests..."
	@echo "------------------------"
	@echo "<not>"


#----------------------------
# Package Environments (Containers)
#----------------------------

#docker run -it --rm -v "$PWD":/srv/app -w /srv/app gavin/bai-bff-dev <command>
build-dev-container: project.clj
	@echo "------------------------"
	@echo "Creating development container..."
	@echo "------------------------"
	@echo "Generating Docker Development Image, from template..."
	@sed -e 's|@@PROJECT@@|$(PROJECT)|g' \
	     -e 's|@@VERSION@@|$(VERSION)|g' \
	     -e 's|@@TAG@@|$(TAG)|g' \
	     -e 's|@@REPO_SITE@@|$(REPO_SITE)|g' \
	     -e 's|@@ORGANIZATION@@|$(ORGANIZATION)|g' \
	     -e 's|@@AUTHOR@@|$(AUTHOR)|g' \
	     -e 's|@@RELEASE_NAME@@|$(RELEASE_NAME)|g' \
	     -e 's|@@JAR_FILE@@|$(JAR_FILE)|g' \
	     -e 's|@@JAR_FILENAME@@|$(JAR_FILENAME)|g' \
	     -e 's|@@JMX_PORT@@|$(JMX_PORT)|g' \
	     -e 's|@@SVC_PORT@@|$(SVC_PORT)|g' $(DOCKER_DEV_TEMPLATE) > $(shell sed -n 's|.*/\(.*\).tmpl|\1|p' <<< $(DOCKER_DEV_TEMPLATE))
	docker build -f $(shell sed -n 's|.*/\(.*\).tmpl|\1|p' <<< $(DOCKER_DEV_TEMPLATE)) \
			-t $(DOCKER_REGISTRY)/$(PROJECT)-dev:$(DOCKER_TAG) \
			-t $(DOCKER_REGISTRY)/$(PROJECT)-dev:latest .
	docker image ls | grep $(PROJECT)-dev


publish-dev-container:
	@echo "------------------------"
	@echo "Publishing development container..."
	@echo "------------------------"
	docker push $(DOCKER_REGISTRY)/$(PROJECT)-dev:$(DOCKER_TAG)
	docker push $(DOCKER_REGISTRY)/$(PROJECT)-dev:latest

build-deploy-container: dist
	@echo "------------------------"
	@echo "Building container'ed artifact... ($(PROFILE))"
	@echo "------------------------"
	@echo "Generating Docker Deployment Image, from template..."
	@sed -e 's|@@PROJECT@@|$(PROJECT)|g' \
	     -e 's|@@VERSION@@|$(VERSION)|g' \
	     -e 's|@@TAG@@|$(TAG)|g' \
             -e 's|@@CHANGE_CAUSE@@|$(CHANGE_CAUSE)|g' \
	     -e 's|@@REPO_SITE@@|$(REPO_SITE)|g' \
	     -e 's|@@ORGANIZATION@@|$(ORGANIZATION)|g' \
	     -e 's|@@AUTHOR@@|$(AUTHOR)|g' \
	     -e 's|@@RELEASE_NAME@@|$(RELEASE_NAME)|g' \
	     -e 's|@@JAR_FILE@@|$(JAR_FILE)|g' \
	     -e 's|@@JAR_FILENAME@@|$(JAR_FILENAME)|g' \
	     -e 's|@@RUN_SCRIPT@@|$(RUN_SCRIPT)|g' \
	     -e 's|@@RUN_SCRIPT_NAME@@|$(RUN_SCRIPT_NAME)|g' \
	     -e 's|@@JMX_PORT@@|$(JMX_PORT)|g' \
	     -e 's|@@SVC_PORT@@|$(SVC_PORT)|g' $(DOCKER_TEMPLATE) > $(shell sed -n 's|.*/\(.*\).tmpl|\1|p' <<< $(DOCKER_TEMPLATE))
	docker build -t $(DOCKER_REGISTRY)/$(PROJECT):$(DOCKER_TAG) \
		     -t $(DOCKER_REGISTRY)/$(PROJECT):latest .
	docker image ls | grep $(DOCKER_TAG)


publish-deploy-container: build-deploy-container
	@echo "------------------------"
	@echo "Publishing container to registry... ($(PROFILE))"
	@echo "------------------------"
	docker push $(DOCKER_REGISTRY)/$(PROJECT):$(DOCKER_TAG)

#----------------------------
# CD Pipeline setup
#----------------------------

cd-pipeline-setup:
	@echo "------------------------"
	@echo "Setting up CD pipeline..."
	@echo "------------------------"
	#create or update the pipeline


#----------------------------
# Deployment
#----------------------------
FORCE: ;

deploy.yml: FORCE
	@echo "Generating kubernetes deploy.yaml from template..."
	@sed -e 's|@@PROJECT@@|$(PROJECT)|g' \
	     -e 's|@@VERSION@@|$(VERSION)|g' \
	     -e 's|@@ENVIRONMENT@@|$(ENVIRONMENT)|g' \
	     -e 's|@@LOGGING_LEVEL@@|$(LOGGING_LEVEL)|g' \
	     -e 's|@@JMX_PORT@@|$(JMX_PORT)|g' \
	     -e 's|@@SVC_PORT@@|$(SVC_PORT)|g' \
	     -e 's|@@REPO_SITE@@|$(REPO_SITE)|g' \
	     -e 's|@@TAG@@|$(TAG)|g' \
	     -e 's|@@CHANGE_CAUSE@@|$(CHANGE_CAUSE)|g' \
	     -e 's|@@DOCKER_REGISTRY@@|$(DOCKER_REGISTRY)|g' \
	     -e 's|@@DOCKER_TAG@@|$(DOCKER_TAG)|g' \
	     -e 's|@@COMMIT_SHORT_HASH@@|$(COMMIT_SHORT_HASH)|g' \
             -e 's|@@THREAD_POOL_SIZE@@|$(THREAD_POOL_SIZE)|g' \
	     -e 's|@@MAX_QUEUE_SIZE@@|$(MAX_QUEUE_SIZE)|g' \
             -e 's|@@KAFKA_DEFAULT_NUM_PARTITIONS@@|$(KAFKA_DEFAULT_NUM_PARTITIONS)|g' \
             -e 's|@@KAFKA_DEFAULT_REPLICATION_FACTOR@@|$(KAFKA_DEFAULT_REPLICATION_FACTOR)|g' \
	     -e 's|@@KAFKA_SOURCE_TOPICS@@|$(KAFKA_SOURCE_TOPICS)|g' \
	     -e 's|@@KAFKA_CONSUMER_GROUP_ID@@|$(KAFKA_CONSUMER_GROUP_ID)|g' \
	     -e 's|@@KAFKA_POLL_INTERVAL_MS@@|$(KAFKA_POLL_INTERVAL_MS)|g' \
	     -e 's|@@KAFKA_SINK_TOPICS@@|$(KAFKA_SINK_TOPICS)|g' \
	     -e 's|@@KAFKA_CMD_SUBMIT_TOPIC@@|$(KAFKA_CMD_SUBMIT_TOPIC)|g' \
	     -e 's|@@KAFKA_CMD_RETURN_TOPIC@@|$(KAFKA_CMD_RETURN_TOPIC)|g' $(DEPLOY_TEMPLATE) > $(DEPLOY_YML)

service.yml: FORCE
	@echo "Generating kubernetes service.yaml from template..."
	@sed -e 's|@@PREFIX_LIST_CIDR_BLOCKS@@|$(shell PATH=$(PATH) kubectl get configmaps outputs-infrastructure --output json | PATH=$(PATH) jq '.data.prefix_list_cidr_blocks')|g' \
	     -e 's|@@PROJECT@@|$(PROJECT)|g' \
	     -e 's|@@ENVIRONMENT@@|$(ENVIRONMENT)|g' \
	     -e 's|@@JMX_PORT@@|$(JMX_PORT)|g' \
	     -e 's|@@SVC_PORT@@|$(SVC_PORT)|g' $(SERVICE_TEMPLATE) > $(SERVICE_YML)

deploy: _deploy_venv deploy.yml service.yml
	@echo "------------------------"
	@echo "K8S deployment..."
	@echo "------------------------"
	#Deploy this service to the k8s cluster
	kubectl $(K8S_KUBECTL_ARGS) apply -f deploy.yml
	kubectl $(K8S_KUBECTL_ARGS) apply -f service.yml
	@touch $(SERVICE_ENDPOINT)
	@while [ ! -s $(SERVICE_ENDPOINT) ]; do \
	  kubectl $(K8S_KUBECTL_ARGS) get service $(PROJECT) -o json | jq '.status.loadBalancer.ingress[].hostname,.spec.ports[0].port' | xargs | sed 's/ /:/' > $(SERVICE_ENDPOINT); \
	  sleep 5; \
	done


undeploy-deployment:
	kubectl $(K8S_KUBECTL_ARGS) delete deployment $(PROJECT) --grace-period=60

undeploy-service:
	kubectl $(K8S_KUBECTL_ARGS) delete service $(PROJECT) --grace-period=60

undeploy: undeploy-deployment undeploy-service
	@echo "------------------------"
	@echo "K8S ***NUKING*** the deployment and service... (softly)"
	@echo "------------------------"

rollback:
	@echo "------------------------"
	@echo "K8S Rollback to the last deployment..."
	@echo "------------------------"
	kubectl $(K8S_KUBECTL_ARGS) rollout undo deployments $(PROJECT)


rollout-history:
	@echo "------------------------"
	@echo "K8S Check Rollout History..."
	@echo "------------------------"
	kubectl $(K8S_KUBECTL_ARGS) rollout history deployment.v1.apps/$(PROJECT)

# (may want to put in the k8s cycle here as well scale up and down)
#----------------------------------------------------------------
.PHONY: all clean clean-all compile deploy dist docs publish release rollback rollout-history test undeploy undeploy-deployment undeploy-service
