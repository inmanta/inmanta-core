FROM fedora:22

RUN dnf install -y git python3 python-virtualenv python3-virtualenv git

# install the server
RUN mkdir -p /opt/impera
RUN mkdir -p /var/lib/impera
ADD . /opt/impera/
RUN virtualenv -p /usr/bin/python3 /opt/impera/env
RUN /opt/impera/env/bin/pip install -r/opt/impera/requirements.txt

CMD PYTHONPATH=/opt/impera/src /opt/impera/env/bin/python3 /opt/impera/bin/impera -c /opt/impera/misc/docker-server.cfg -vvv server
EXPOSE 8888
