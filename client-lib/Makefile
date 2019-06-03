ENV_NAME = client-lib

include ../python-common.mk

PYTEST = $(CONDA_RUN) tox --recreate --

deploy.yml:
	# A dummy file since client-lib is not a Kubernetes service
	touch deploy.yml
