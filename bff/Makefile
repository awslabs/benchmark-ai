#----------------------------------------------------------------
# Project Specific Info
#----------------------------------------------------------------
PROJECT := bai-bff
ORGANIZATION := MXNet Berlin
RELEASE_NAME := flatbush
PROFILE := prod
AUTHOR := Gavin M. Bell
REPO_SITE = https://github.com/MXNetEdge/benchmark-ai/$(PROJECT)

RESOURCE_PATHS := resources
SOURCE_PATHS := src
TEST_PATHS := test
BIN_PATH := bin

#Created file structures...
COMPILE_PATH := target/classes
TARGET_PATH := target
RELEASE_PATH := release
GEN_DOCS_PATH := docs-generated

MAIN := bai-bff.app

#---
# Continuous Delivery, Packaging and Containerization
#---
DOCKER_REGISTRY := I_DUNNO
SERVICE_DIRECTORY_PAGE := http://foo.bar.com/services/$(PROJECT)

CD_SERVER := http://foo.bar.com/job/$(PROJECT)
CD_PACKAGE_VERSION_STAMP := FIXME
CD_RUNTIME_STACK := clojure
CD_MANIFEST := manifest.json
CD_TARGET_PATH := target
#----------------------------------------------------------------

#(note: may set VERSION variable in above stanza to override the default below, which gets it from the nearest git tag of the form v.#.#.#<blah>)
VERSION ?= $(shell git tag | sed -n -e 's/^v\([0-9]*\.[0-9]*\.[0-9]*\).*/\1/p' | sort -s -u -t. -k1,1n -k2,2n -k3,3n | tail -n 1)
MODULE := $(shell git describe | sed -n 's/\(.*\)-[0-9].*/\1/p' | xargs) #TODO: set tp docker container id
BRANCH := $(shell git branch | grep '*' | sed -n 's/\*[ ]*//p' | xargs)
COMMIT := $(shell git log -p -n1 | sed -n -e 's/^commit \(.*\)/\1/p'   | xargs)
COMMIT_DATE :=   $(shell git log -p -n1 | sed -n -e 's/^Date: \(.*\)/\1/p'   | xargs)
COMMIT_AUTHOR := $(shell git log -p -n1 | sed -n -e 's/^Author: \(.*\)/\1/p' | xargs)
BUILD_DATE := $(shell date)

TEMPLATE := etc/project.clj.tmpl

LEIN_ROOT := true
LEIN := ./bin/lein

JAR_FILE := $(TARGET_PATH)/$(PROJECT)-$(VERSION)-standalone.jar

TARGET := $(PROJECT)-$(VERSION)
RELEASE_FILE := $(TARGET).tar.gz

CLJ_FILES := $(shell find $(SOURCE_PATHS) -name '*.clj')
CLJ_TEST_FILES := $(shell find $(TEST_PATHS) -name '*.clj')
MAIN_CLASS_FILE := $(COMPILE_PATH)/$(shell sed -e 's@\.@/@g' -e 's@-@_@g' <<<$(MAIN))__init.class

compile: $(MAIN_CLASS_FILE)

$(MAIN_CLASS_FILE): project.clj $(CLJ_FILES)
	$(LEIN) compile
	@touch $@

all: test docs dist

show-vars:
	@echo "----------------------------------"
	@echo "VERSION =  $(VERSION)"
	@echo "PROJECT = $(PROJECT)"
	@echo "ORGANIZATION = $(ORGANIZATION)"
	@echo "RELEASE_NAME = $(RELEASE_NAME)"
	@echo "PROFILE = $(PROFILE)"
	@echo "AUTHOR = $(AUTHOR)"
	@echo "REPO_SITE = $(REPO_SITE)"
	@echo "RESOURCE_PATHS = $(RESOURCE_PATHS)"
	@echo "SOURCE_PATHS = $(SOURCE_PATHS)"
	@echo "TEST_PATHS = $(TEST_PATHS)"
	@echo "BIN_PATH := $(BIN_PATH)"
	@echo "COMPILE_PATH = $(COMPILE_PATH)"
	@echo "TARGET_PATH = $(TARGET_PATH)"
	@echo "RELEASE_PATH = $(RELEASE_PATH)"
	@echo "MAIN = $(MAIN)"
	@echo "BUILD_DATE = $(BUILD_DATE)"
	@echo "----------------------------------"
	@echo "SERVICE_DIRECTORY_PAGE : $(SERVICE_DIRECTORY_PAGE)"
	@echo "DOCKER_REGISTRY        : $(DOCKER_REGISTRY)"
	@echo "Package Version     : $(CD_PACKAGE_VERSION_STAMP)"
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
	     -e 's|@@VERSION@@|$(VERSION)|g' \
	     -e 's|@@CD_PACKAGE_VERSION_STAMP@@|$(CD_PACKAGE_VERSION_STAMP)|g' \
	     -e 's|@@MODULE@@|$(MODULE)|g' \
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
	$(LEIN) clean
	rm -rf $(TARGET_PATH)

clean-all: clean
	rm -rf $(RELEASE_PATH)
	rm -rf $(COMPILE_PATH)
	rm -rf $(GEN_DOCS_PATH)
	rm project.clj
	rm -rf $(CD_TARGET_PATH)

$(JAR_FILE): $(MAIN_CLASS_FILE)
	@echo "------------------------"
	@echo "Building Jar"
	@echo "------------------------"
	LEIN_SNAPSHOTS_IN_RELEASE=1 ${LEIN} with-profile $(PROFILE) uberjar
	@unzip -q -c $(JAR_FILE) META-INF/MANIFEST.MF


dist:	$(JAR_FILE)

run:	compile
	$(LEIN) run

docs:	compile
	$(LEIN) codox
	$(LEIN) cloverage
	$(LEIN) vanity

#----------------------------
# Testing...
#----------------------------

test: compile
	@echo "------------------------"
	@echo "Runnig Unit Tests..."
	@echo "------------------------"
	@$(LEIN) with-profile test

integration-test: compile
	@echo "------------------------"
	@echo "Running Integration Tests..."
	@echo "------------------------"



#----------------------------
# Package Environments (Containers)
#----------------------------

create-dev-container:
	@echo "------------------------"
	@echo "Creating development container..."
	@echo "------------------------"


publish-dev-container:
	@echo "------------------------"
	@echo "Publishing development container..."
	@echo "------------------------"


build-deploy-container:
	@echo "------------------------"
	@echo "Build artifact in container..."
	@echo "------------------------"
	#docker pull

publish-container:
	@echo "------------------------"
	@echo "Publishing container to registry..."
	@echo "------------------------"



#----------------------------
# CD Pipeline setup
#----------------------------

cd-pipeline-setup:
	@echo "------------------------"
	@echo "Setting up CD pipeline..."
	@echo "------------------------"
	#create or update the pipeline

deploy:
	@echo "------------------------"
	@echo "Setting up CD pipeline..."
	@echo "------------------------"
	#Deploy this code to the k8s cluster


# (may want to put in the k8s cycle here as well scale up and down)
#----------------------------------------------------------------
.PHONY: test all docs release clean clean-all compile dist cd-pipeline cd-prepare cd-publish cd-promote container-test
