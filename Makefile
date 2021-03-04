# Shortcuts for various dev tasks. Based on makefile from pydantic
.DEFAULT_GOAL := all
isort = isort src tests tests_common
black = black src tests tests_common

.PHONY: install
install:
	pip install -U setuptools pip
	pip install -U -r requirements.txt -r requirements.dev.txt
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

.PHONY: mypy mypy-diff mypy-save
RUN_MYPY=MYPYPATH=stubs:src python -m mypy --html-report mypy -p inmanta

mypy:
	$(RUN_MYPY)

# baseline file mypy-diff will compare to
MYPY_BASELINE_FILE=.mypy-baseline
# temporary file used to store most recent mypy run
MYPY_TMP_FILE=.mypy-tmp
# temporary file used to store baseline with line numbers filtered out
MYPY_BASELINE_FILE_NO_LN_NB=$(MYPY_BASELINE_FILE).nolnnb
# prepare file for diff: remove last 2 lines and filter out line numbers
MYPY_DIFF_PREPARE=head -n -2 | sed 's/^\(.\+:\)[0-9]\+\(:\)/\1\2/'
# read old/new line number (format +n for new or -n for old) from stdin and transform to old/new line
MYPY_DIFF_FETCH_LINES=xargs -I{} sh -c 'sed -n -e "s/^/$(MYPY_SET_COLOUR)$$(echo {} | cut -c 1 -) /" -e "$$(echo {} | cut -c 2- -)p" $(MYPY_SELECT_FILE)'
MYPY_SELECT_FILE=$$(if [[ "{}" == +* ]]; then echo $(MYPY_TMP_FILE); else echo $(MYPY_BASELINE_FILE); fi)
MYPY_SET_COLOUR=$$(if [[ "{}" == +* ]]; then tput setaf 1; else tput setaf 2; fi)
# diff line format options
LFMT_LINE_NB=%dn
LFMT_NEWLINE=%c'\\012'

# compare mypy output with baseline file, show newly introduced and resolved type errors
mypy-diff:
	@ # run mypy and temporarily save result
	@ $(RUN_MYPY) > $(MYPY_TMP_FILE) || true
	@ # prepare baseline for diff and temporarily save result
	@ cat $(MYPY_BASELINE_FILE) | $(MYPY_DIFF_PREPARE) > $(MYPY_BASELINE_FILE_NO_LN_NB) || true
	@ # prepare most recent mypy output and run diff, returing +n for new lines and -n for old lines, where n is the line number
	@ cat $(MYPY_TMP_FILE) | $(MYPY_DIFF_PREPARE) | diff $(MYPY_BASELINE_FILE_NO_LN_NB) - \
		--new-line-format="+$(LFMT_LINE_NB)$(LFMT_NEWLINE)" \
		--old-line-format="-$(LFMT_LINE_NB)$(LFMT_NEWLINE)" \
		--unchanged-line-format='' \
		--unidirectional-new-file \
		| $(MYPY_DIFF_FETCH_LINES) \
		|| true
	@ # cleanup
	@ rm -f $(MYPY_TMP_FILE) $(MYPY_BASELINE_FILE_NO_LN_NB)

# save mypy output to baseline file
mypy-save:
	$(RUN_MYPY) > $(MYPY_BASELINE_FILE) || true

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

