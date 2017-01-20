#!/bin/bash

setenforce 0

sudo dnf install -y git python3 python-virtualenv python3-virtualenv python3-tox python3-nose rpm-build python-tox gcc
sudo mkdir -p /opt/inmanta
sudo python3 -m virtualenv -p python3 /opt/inmanta/env
sudo /opt/inmanta/env/bin/pip install -r /inmanta/requirements.txt
