FROM centos:7
ARG branch

# Pin the base-url of the epel repo to ensure stability
COPY misc/epel.repo /etc/yum.repos.d/epel.repo
RUN curl --silent --location https://dl.yarnpkg.com/rpm/yarn.repo >/etc/yum.repos.d/yarn.repo
RUN yum install -y \
		git \
		sudo \
		tar \
		findutils \
		make \
		procps-ng \
		python3-devel \
		nodejs-grunt-cli \
		gcc-c++ \
		gcc \
		make \
		yarn \
		postgresql

# install the server
RUN mkdir -p /opt/inmanta
RUN mkdir -p /var/lib/inmanta
RUN python3 -m venv /opt/inmanta/env
RUN /opt/inmanta/env/bin/pip install -U pip

# install the dashboard
RUN git clone https://github.com/inmanta/inmanta-dashboard
RUN (cd inmanta-dashboard; yarn install; grunt dist; mkdir -p /usr/share/inmanta/; mv dist /usr/share/inmanta/dashboard)

RUN mkdir -p /etc/inmanta/inmanta.d

COPY . /code
COPY misc/docker-server.cfg /etc/inmanta/server.cfg

RUN /opt/inmanta/env/bin/pip install -U -r/code/requirements.txt
RUN /opt/inmanta/env/bin/pip install /code

CMD until PGPASSWORD="postgres" psql -h "postgres" -U "postgres" -c '\q'; do sleep 1; done && /opt/inmanta/env/bin/python3 -m inmanta.app -c /etc/inmanta/server.cfg -vvv server
EXPOSE 8888
