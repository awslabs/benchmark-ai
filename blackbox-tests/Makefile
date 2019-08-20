ENV_NAME = blackbox-tests

# Use `build` as default because we don't want coverage
default: build

include ../etc/base-common.mk
include ../etc/python-common.mk

PYTEST = pytest -s
# Make coverage flags empty because there is no need for coverage.
COVERAGE_FLAGS =

_post_venv::
	$(PIP) install -r requirements.txt

publish:
	echo "Nothing to publish"
