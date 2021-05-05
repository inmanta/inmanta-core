#!/usr/bin/env sh

# start inmanta app to generate parser/lexer in place
env=$(mktemp -d)
python3 -m venv ${env}
${env}/bin/python3 -m pip install -U pip
${env}/bin/python3 -m pip install -e .
${env}/bin/python3 -m inmanta.app -h
rm -r ${env}

# prepare pytest-inmanta-extensions build
python3 tests_common/copy_files_from_core.py
