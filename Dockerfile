FROM fedora:22

RUN dnf install -y git python3 python-virtualenv python3-virtualenv git

# install the server
RUN mkdir -p /opt/inmanta
RUN mkdir -p /var/lib/inmanta
ADD . /opt/inmanta/
RUN virtualenv -p /usr/bin/python3 /opt/inmanta/env
RUN /opt/inmanta/env/bin/pip install -r/opt/inmanta/requirements.txt

CMD PYTHONPATH=/opt/inmanta/src /opt/inmanta/env/bin/python3 /opt/inmanta/bin/inmanta -c /opt/inmanta/misc/docker-server.cfg -vvv server
EXPOSE 8888
