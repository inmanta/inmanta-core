FROM fedora:24

RUN dnf install -y git python3 python-virtualenv python3-virtualenv git nodejs-grunt-cli

# install the server
RUN mkdir -p /opt/inmanta
RUN mkdir -p /var/lib/inmanta
ADD . /opt/inmanta/
RUN virtualenv -p /usr/bin/python3 /opt/inmanta/env
RUN /opt/inmanta/env/bin/pip install -r/opt/inmanta/requirements.txt

# install the dashboard
RUN git clone https://github.com/inmanta/inmanta-dashboard
RUN (cd inmanta-dashboard; npm install; grunt dist; mkdir -p /usr/share/inmanta/; mv dist /usr/share/inmanta/dashboard)

CMD PYTHONPATH=/opt/inmanta/src /opt/inmanta/env/bin/python3 /opt/inmanta/bin/inmanta -c /opt/inmanta/misc/docker-server.cfg -vvv server
EXPOSE 8888
