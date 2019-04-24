SHELL :=/bin/bash
ENV_NAME = kafka-utils-test
CONDA_RUN = conda run -n $(ENV_NAME)
PYTHON = python
PYTEST = pytest
TEST_FLAGS = -v
COVERAGE_FLAGS = --cov=src --cov-report html --cov-fail-under 90

venv:
	conda env create -f test-environment.yml --force

develop: venv
	$(CONDA_RUN) $(PYTHON) setup.py develop

install: venv
	$(CONDA_RUN) $(PYTHON) setup.py install

test: develop
	$(CONDA_RUN) $(PYTEST) $(TEST_FLAGS)

coverage: develop
	$(CONDA_RUN) $(PYTEST) $(TEST_FLAGS) $(COVERAGE_FLAGS)
