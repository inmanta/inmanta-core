# Shortcuts for various dev tasks. Based on makefile from pydantic
.DEFAULT_GOAL := all
isort = isort src tests tests_common
black = black src tests tests_common

.PHONY: install
install:
	pip install -U setuptools pip uv -c requirements.txt
	uv pip install -U -e . -c requirements.txt -r requirements.dev.txt

.PHONY: install-tests
install-tests:
	pip install -U setuptools pip
	python3 tests_common/copy_files_from_core.py
	pip install -e ./tests_common

.PHONY: format
format:
	$(isort)
	$(black)

.PHONY: pep8
pep8:
	uv pip install -c requirements.txt pep8-naming flake8-black flake8-isort
	flake8 src tests tests_common

RUN_MYPY=MYPYPATH=stubs:src python -m mypy --soft-error-limit=-1 --html-report mypy -p inmanta

.PHONY: mypy
mypy:
	$(RUN_MYPY) | mypy-baseline filter

.PHONY: mypy-sync
mypy-sync:
	$(RUN_MYPY) | mypy-baseline sync

.PHONY: mypy-full
mypy-full:
	$(RUN_MYPY)

.PHONY: test
test:
	pytest -vvv --log-level DEBUG tests

.PHONY: testcov
testcov:
	pytest --cov=inmanta --cov-report html:coverage --cov-report term -vvv tests

.PHONY: all
all: pep8 test mypy

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

