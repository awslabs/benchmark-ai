ENV_NAME = kafka-utils-test

include ../etc/base-common.mk
include ../python-common.mk
include ../etc/docker-common.mk

publish:
	echo "Nothing to publish"

# Copy paste from fetcher
PROJECT=kafka-utils

STAGE ?= devo

_post_venv::
	$(PIP) install -r requirements.txt

.PHONY: integration_tests

ifeq ($(STAGE),local)
include ../etc/deploy-common.mk
#Pass special label designed for local integration tests
  DOCKER_IMAGE_LABEL=local-latest
  TEST_LABEL=DOCKER_IMAGE_LABEL=$(DOCKER_IMAGE_LABEL)
else
  TEST_LABEL=
include ../etc/base-common.mk
endif

integration_tests:
	echo $(TEST_LABEL)
	cd $(INTEGRATION_TEST_FOLDERS) && $(MAKE) run $(TEST_LABEL)
