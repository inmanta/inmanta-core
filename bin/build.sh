#!/bin/bash +xe

if [[ $# -ne 2 ]]; then
    echo "Usage: build.sh buildconf RELEASE" >&2
    exit 1
fi

if [[ ! -a $1 ]]; then 
    echo "Unable to find buildconf file, pass it as arg 1" >&2
    exit 1
fi

CONF=$(grep -e "^$2" < $1)

if [[ -z $CONF ]]; then
    echo "Unable to find build target $2" >&2
    exit 1
fi

set -- $CONF

DIST=$1
OS=$2
VERSION=$3
SCRIPT=$4

ln -sf docker/$OS/Dockerfile .
sed -i "s/^FROM .*/FROM $OS:$VERSION/g" Dockerfile 
mkdir -p build-result/$DIST
rm -rf buidl-result/$DIST/*

docker build -t imp-$DIST-build-env .
docker run -v $(pwd)/build-result:/builds imp-$DIST-build-env bash $SCRIPT /builds/$DIST

rsync -a -e "ssh -p 1212 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=no" --delete --progress build-result/$DIST jenkins@impera.io:/srv/www/impera/repo/
