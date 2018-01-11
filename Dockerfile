FROM fedora:27

RUN dnf install -y git python3 python3-devel python-virtualenv python3-virtualenv git nodejs-grunt-cli gcc-c++ gcc make

# install the server
RUN mkdir -p /opt/inmanta
RUN mkdir -p /var/lib/inmanta
ADD . /opt/inmanta/
RUN virtualenv -p /usr/bin/python3 /opt/inmanta/env
RUN /opt/inmanta/env/bin/pip install -r/opt/inmanta/requirements.txt
RUN /opt/inmanta/env/bin/pip install /opt/inmanta

# install the dashboard
RUN git clone https://github.com/inmanta/inmanta-dashboard
RUN (cd inmanta-dashboard; npm install -g bower; npm install; bower install --allow-root; grunt dist; mkdir -p /usr/share/inmanta/; mv dist /usr/share/inmanta/dashboard)

CMD PYTHONPATH=/opt/inmanta/src /opt/inmanta/env/bin/python3 /opt/inmanta/env/bin/inmanta -c /opt/inmanta/misc/docker-server.cfg -vvv server
EXPOSE 8888
