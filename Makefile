# Shortcuts for various dev tasks. Based on makefile from pydantic
.DEFAULT_GOAL := all
isort = isort -rc src tests tests_common
black = black src tests tests_common

.PHONY: install
install:
	pip install -U setuptools pip
	pip install -U -r requirements.txt
	pip install -e .

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
	pip install -c requirements.txt pep8-naming flake8-black flake8-isort
	flake8 src tests tests_common

.PHONY: mypy mypy-diff mypy-commit
RUN_MYPY=MYPYPATH=stubs:src python -m mypy --html-report mypy -p inmanta

mypy:
	$(RUN_MYPY)

MYPY_TMP_FILE=.mypy-tmp
MYPY_BASELINE_FILE=.mypy-baseline
MYPY_BASELINE_FILE_NO_LN_NB=$(MYPY_BASELINE_FILE).nolnnb
MYPY_DIFF_PREPARE=head -n -2 | sed 's/^\(.\+:\)[0-9]\+\(:\)/\1\2/'
MYPY_SELECT_FILE=$$(if [[ "{}" == +* ]]; then echo $(MYPY_TMP_FILE); else echo $(MYPY_BASELINE_FILE); fi)
MYPY_SET_COLOUR=$$(if [[ "{}" == +* ]]; then tput setaf 1; else tput setaf 2; fi)
MYPY_DIFF_LN_NB_TO_LN=xargs -I{} sh -c 'sed -n -e "s/^/$(MYPY_SET_COLOUR)$$(echo {} | cut -c 1 -) /" -e "$$(echo {} | cut -c 2- -)p" $(MYPY_SELECT_FILE)'

mypy-diff:
	@ $(RUN_MYPY) > $(MYPY_TMP_FILE) || true
	@ cat $(MYPY_BASELINE_FILE) | $(MYPY_DIFF_PREPARE) > $(MYPY_BASELINE_FILE_NO_LN_NB) || true
	@ cat $(MYPY_TMP_FILE) | $(MYPY_DIFF_PREPARE) | diff $(MYPY_BASELINE_FILE_NO_LN_NB) - \
		--new-line-format=$$'+%dn%c\'\\012\'' \
		--old-line-format=$$'-%dn%c\'\\012\'' \
		--unchanged-line-format='' \
		--unidirectional-new-file \
		| $(MYPY_DIFF_LN_NB_TO_LN) \
		|| true
	@ rm -f $(MYPY_TMP_FILE) $(MYPY_BASELINE_FILE_NO_LN_NB)

mypy-save:
	$(RUN_MYPY) > $(MYPY_BASELINE_FILE) || true

.PHONY: test
test:
	pytest -vvv tests

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

