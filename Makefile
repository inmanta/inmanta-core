# variables exposed to Jenkinsfile
PYTHON := python3
TESTS := tests
INSTALL_EXTRA_ARGS :=
PYTEST_EXTRA_ARGS :=

# Shortcuts for various dev tasks. Based on makefile from pydantic
.DEFAULT_GOAL := all
isort = isort src tests tests_common
black = black src tests tests_common

ifeq ($(shell which uv),)
pip = $(PYTHON) -m pip
pip_args :=
else
pip := uv pip
pip_args = --python $(PYTHON)
endif

.PHONY: install
install:
	$(pip) install $(pip_args) -U setuptools pip uv -c requirements.txt $(INSTALL_EXTRA_ARGS)
	$(pip) install $(pip_args) -U -e .[dev] -c requirements.txt $(INSTALL_EXTRA_ARGS)

.PHONY: install-tests
install-tests:
	$(pip) install -U setuptools pip uv
	python3 tests_common/copy_files_from_core.py
	$(pip) install -e ./tests_common

.PHONY: format
format:
	$(isort)
	$(black)

.PHONY: pep8 ci-pep8
pep8:
	$(PYTHON) -m flake8 src tests tests_common
ci-pep8: pep8

RUN_MYPY=MYPYPATH=stubs:src $(PYTHON) -m mypy --soft-error-limit=-1 --html-report mypy -p inmanta

# TODO: mypy-baseline config file: sorting
.PHONY: mypy ci-mypy
mypy:
	$(RUN_MYPY) | mypy-baseline filter
ci-mypy: mypy

.PHONY: mypy-sync
mypy-sync:
	$(RUN_MYPY) | mypy-baseline sync

.PHONY: mypy-full
mypy-full:
	$(RUN_MYPY)

.PHONY: test ci-test
test:
	$(PYTHON) -m pytest -vvv --log-level DEBUG $(TESTS)
ci-test:
	$(PYTHON) -m pytest -vvv --log-level DEBUG -p no:sugar --junitxml=junit-test.xml $(PYTEST_EXTRA_ARGS) $(TESTS)

.PHONY: all
all: pep8 test mypy

venv-%: FORCE $(shell mktemp -d)/bin/python install %
	rm -rf $(<:/bin/python=)

%/bin/python: %
	$(PYTHON) -m venv $?
	$(eval PYTHON=$@)

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf mypy
	rm -rf coverage
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	find -name .env | xargs rm -rf
	python setup.py clean
	make -C docs clean

.PHONY: docs
docs:
	make -C docs html

FORCE:
