SHELL :=/bin/bash
CONDA_RUN = conda run --name $(ENV_NAME)
PYTHON = $(CONDA_RUN) python
PIP = $(CONDA_RUN) pip
PYTEST = $(CONDA_RUN) pytest
TEST_FLAGS = -v

TEST_FOLDERS=tests
SRC_FOLDERS=src
INTEGRATION_TEST_FOLDERS=integration_tests

# We mentally do --cov-fail-under 90
COVERAGE_FLAGS = --cov=$(SRC_FOLDERS) --cov-report html --cov-report term

LINT = $(CONDA_RUN) flake8

FORMAT = $(CONDA_RUN) black
FORMAT_FLAGS = --line-length=120

.DEFAULT_GOAL := default

clean:
	rm -rf build/
	rm -rf dist/
	find . -name '*.egg-info' -exec rm -fr {} +
	rm -rf htmlcov
	rm -rf .pytest_cache
	find . -name '__pycache__' -exec rm -fr {} +
	rm -f .coverage

#Things to run before - extendable
_pre_venv::
	echo "Pre env actions"
	conda install --channel conda-forge --name base conda==4.6.14 --yes

#venv body - replacable
_venv: _pre_venv
	conda env update --file environment.yml --prune --name $(ENV_NAME)
	conda env update --file test-environment.yml --name $(ENV_NAME)

#Things to run after - extendable
_post_venv::_venv
	echo "Post env actions"

venv: _post_venv
	echo "Env done"

develop: venv
	$(PYTHON) setup.py develop



test: develop
	$(PYTEST) $(TEST_FLAGS) $(TEST_FOLDERS)

coverage: develop
	$(PYTEST) $(TEST_FLAGS) $(COVERAGE_FLAGS)

lint: venv
	$(LINT) --config=../.flake8 $(SRC_FOLDERS)
	$(LINT) --config=../.flake8 $(TEST_FOLDERS)

build: clean lint coverage

install: build
	$(PYTHON) setup.py install

format: venv _format
_format:
	$(FORMAT) $(FORMAT_FLAGS) setup.py
	$(FORMAT) $(FORMAT_FLAGS) $(SRC_FOLDERS)
	$(FORMAT) $(FORMAT_FLAGS) $(TEST_FOLDERS)

default: install
