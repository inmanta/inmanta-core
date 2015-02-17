FROM ubuntu:latest

RUN apt-get update; apt-get install -y python3 python3-pip git python3-dev devscripts python3-all debhelper; apt-get clean
RUN mkdir /code
WORKDIR /code
ADD bin/ubuntu-package.sh /code/
Add docker/ubuntu/deps /code/

VOLUME /builds
CMD bash ubuntu-package.sh /builds
