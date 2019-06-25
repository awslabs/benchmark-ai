ENV_NAME = blackbox-tests

include ../python-common.mk

PYTEST = pytest -s
COVERAGE_FLAGS =

_post_venv::
	$(PIP) install -r requirements.txt

publish:
	echo "Nothing to publish"

default: build