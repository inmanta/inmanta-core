FROM fedora:latest

RUN yum install -y copr-cli rpm-build python3 python3-pip git rpmdevtools python3-devel createrepo yum-utils
RUN yum clean all
RUN mkdir /code
WORKDIR /code
ADD bin/fedora-package.sh /code/
Add docker/fedora/deps /code/

VOLUME /builds
CMD bash fedora-package.sh /builds
