# Declare base targets which should be overriden if required
CONDA_RUN = conda run --name $(ENV_NAME)
CONDA_ROOT = $(shell conda info --root)
CONDA_ENV_BIN = $(CONDA_ROOT)/envs/$(ENV_NAME)/bin
export PATH := $(CONDA_ENV_BIN):$(PATH)

.DEFAULT_GOAL := build

deploy:
	echo "Nothing to deploy for $(PROJECT)"

undeploy:
	echo "Nothing to undeploy for $(PROJECT)"

build:
	echo "Nothing to build for $(PROJECT)"