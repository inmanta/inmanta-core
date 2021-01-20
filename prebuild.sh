#!/usr/bin/env sh

# add source to path
export PYTHONPATH="$(pwd)/src"

# start inmanta app to generate parser/lexer in place
env=$(mktemp -d)
python3 -m venv ${env}
${env}/bin/python3 -m pip install -U pip
${env}/bin/python3 -m pip install -e .
${env}/bin/python3 -m inmanta.app -h
rm -r ${env}
