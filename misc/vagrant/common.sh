#!/bin/bash

setenforce 0

sudo dnf install -y git python3 python-virtualenv python3-virtualenv python3-tox python3-nose rpm-build python-tox gcc
sudo mkdir -p /opt/impera
sudo virtualenv-3.4 -p python3 /opt/impera/env
sudo /opt/impera/env/bin/pip install -r /inmanta/requirements.txt
