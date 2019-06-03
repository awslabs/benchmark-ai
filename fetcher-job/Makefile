ENV_NAME = fetcher-job

include ../python-common.mk

PROJECT=fetcher-job

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt

deploy.yml:
	# A dummy file since fetcher-job is not a Kubernetes service
	touch deploy.yml
