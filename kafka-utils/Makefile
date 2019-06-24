ENV_NAME = kafka-utils-test

include ../docker-common.mk
include ../python-common.mk

publish:
	echo "Nothing to publish"

deploy.yml:
	echo "Skipping deploy.yml step since kafka-utils does not have to be deployed"
	touch deploy.yml

# Copy paste from fetcher
PROJECT=kafka-utils

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

.PHONY: integration_tests

ifeq ($(STAGE),local)
#Pass special label designed for local integration tests
  DOCKER_IMAGE_LABEL=local-latest
  TEST_LABEL=DOCKER_IMAGE_LABEL=$(DOCKER_IMAGE_LABEL)
else
  TEST_LABEL=
endif

integration_tests:
	echo $(TEST_LABEL)
	cd $(INTEGRATION_TEST_FOLDERS) && $(MAKE) run $(TEST_LABEL)
