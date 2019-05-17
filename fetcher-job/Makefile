ENV_NAME = fetcher-job

include ../python-common.mk

DOCKER_IMAGE_TAG=stsukrov/datafetcher

include ../docker-common.mk

_post_venv::
	$(PIP) install -r requirements.txt

