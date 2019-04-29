SHELL :=/bin/bash
ENV_NAME = kafka-utils-test
CONDA_RUN = conda run --name $(ENV_NAME)
PYTHON = $(CONDA_RUN) python
PYTEST = $(CONDA_RUN) pytest
TEST_FLAGS = -v
# We mentally do --cov-fail-under 90
COVERAGE_FLAGS = --cov=src --cov-report html --cov-report term


LINT = $(CONDA_RUN) flake8

.DEFAULT_GOAL := default

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf **/*.egg-info
	rm -rf htmlcov
	rm -rf .pytest_cache
	rm -f .coverage

venv:
	conda install --channel conda-forge --name base conda==4.6.14 --yes
	conda env update --file environment.yml --prune
	conda env update --file test-environment.yml --prune

develop: venv
	$(PYTHON) setup.py develop

install: venv
	$(PYTHON) setup.py install

test: develop
	$(PYTEST) $(TEST_FLAGS)

coverage: develop
	$(PYTEST) $(TEST_FLAGS) $(COVERAGE_FLAGS)

lint: venv
	$(LINT) ./

default: clean lint coverage install
