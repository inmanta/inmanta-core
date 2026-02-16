# variables exposed to Jenkinsfile
PYTHON := python3
ISO_VERSION :=
PIP_INDEX :=
TESTS := tests
PYTEST_EXTRA_ARGS :=

.DEFAULT_GOAL := all
isort = isort src tests $(wildcard tests_common)
black = black src tests $(wildcard tests_common)
packages := $(notdir $(patsubst %.egg-info,,$(wildcard src/*)))
mypy = MYPYPATH=stubs:src $(PYTHON) -m mypy --soft-error-limit=-1 --html-report mypy $(addprefix -p , $(packages))
mypy_baseline = $(PYTHON) -m mypy_baseline

ifdef PIP_INDEX
pip_index_arg := -i $(PIP_INDEX)
endif
uv_args = pip install --python $(PYTHON) --prerelease if-necessary-or-explicit $(pip_index_arg)
ifeq ($(shell which uv),)
bootstrap_pip_install = $(PYTHON) -m pip install $(pip_index_arg)
else
bootstrap_pip_install = uv $(uv_args)
endif
# pip install to use after installing uv in the venv
pip_install = $(PYTHON) -m uv $(uv_args)
ifdef ISO_VERSION
pip_install_c = $(pip_install) -c requirements.txt -c 'https://docs.inmanta.com/inmanta-service-orchestrator-dev/$(ISO_VERSION)/reference/requirements.txt'
else
pip_install_c = $(pip_install) -c requirements.txt
endif

src_dirs := src tests $(wildcard tests_common)

parser:=src/inmanta/parser/
ifeq ($(wildcard $(parser)/plyInmantaParser.py),)
# no parser present in this package => no parsetab prerequisite
parsetab:=
else
parsetab:=$(parser)/parsetab.py
# load inmanta.app so that the parser is generated for a consistent mypy baseline
$(parsetab): $(parser)/plyInmantaLex.py $(parser)/plyInmantaParser.py
	$(PYTHON) -m inmanta.app >/dev/null
	touch $@
endif

.PHONY: install ci-install ci-install-check
install:
	$(bootstrap_pip_install) -U setuptools pip uv
	$(pip_install_c) -U -e .[dev]

ci-install-check:
ifeq ($(shell which uv),)
	$(error uv is required for this target.)
endif
ifndef ISO_VERSION
	$(error ISO_VERSION make variable needs to be set for this target. Run `make ISO_VERSION=<x> $@`.)
endif

# some tests are skipped for editable installs => no editable on ci
# first perform editable install to install parsetab file (mypy reads it locally, even for non-editable install)
ci-install: ci-install-check install $(parsetab)
	$(pip_install_c) -U .[dev]

.PHONY: install-tests
install-tests:
	$(bootstrap_pip_install) -U setuptools pip uv
	$(PYTHON) tests_common/copy_files_from_core.py
	$(pip_install) -e ./tests_common

.PHONY: format
format:
	$(isort)
	$(black)

.PHONY: pep8 ci-pep8
pep8:
	$(PYTHON) -m flake8 $(src_dirs)
ci-pep8:
	$(PYTHON) -m flake8 --output-file flake8-report.txt --tee $(src_dirs)
	$(PYTHON) -m junit_conversor flake8-report.txt junit-pep8.xml

.PHONY: mypy ci-mypy
mypy: $(parsetab)
	$(mypy) | $(mypy_baseline) filter --sort-baseline
ci-mypy: $(parsetab)
	$(mypy) --junit-xml junit-mypy.xml --cobertura-xml-report coverage | $(mypy_baseline) filter --no-colors --sort-baseline

.PHONY: mypy-sync
mypy-sync: $(parsetab)
	$(mypy) | $(mypy_baseline) sync --sort-baseline

.PHONY: mypy-full
mypy-full: $(parsetab)
	$(mypy)

.PHONY: test ci-test
test:
	$(PYTHON) -m pytest -vvv --log-level DEBUG $(TESTS)
ci-test:
	$(PYTHON) -m pytest -vvv --log-level DEBUG -p no:sugar --junitxml=junit-tests.xml $(PYTEST_EXTRA_ARGS) $(TESTS)

.PHONY: all ci-all
all: pep8 mypy test
ci-all: ci-pep8 ci-mypy ci-test

# The python path must be the first prerequisite, because it is referenced as $< in the recipe
venv-%: $(shell mktemp -d)/bin/python install % FORCE
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
	make -C docs move_openapi_after_docs_builds

FORCE:
