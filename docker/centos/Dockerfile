FROM fedora:latest

RUN yum install -y centos-release-SCL rpm-build git yum-utils createrepo rpmdevtools
RUN yum install -y python33 python33-python-setuptools python33-python-devel
RUN yum clean all
RUN mkdir /code
WORKDIR /code
ADD bin/fedora-package.sh /code/
Add docker/centos/deps /code/

VOLUME /builds
CMD scl enable python33 "bash -ex fedora-package.sh /builds"
