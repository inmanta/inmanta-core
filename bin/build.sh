#!/bin/bash +xe

if [[ $# -ne 4 ]]; then
    echo "Usage: build.sh buildconf RELEASE repo latest|dev" >&2
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

REPO=$3
TARGET=$4

set -- $CONF

DIST=$1
OS=$2
VERSION=$3
SCRIPT=$4

ln -sf docker/$OS/Dockerfile .
sed -i "s/^FROM .*/FROM $OS:$VERSION/g" Dockerfile 
mkdir -p build-result/$DIST
rm -rf build-result/$DIST/*

mkdir -p build-result/$TARGET/$DIST

docker build -t impera-$DIST-build-env .
docker run -v $(pwd)/build-result:/builds impera-$DIST-build-env bash $SCRIPT /builds/$TARGET/$DIST $REPO $TARGET

#rsync -a -e "ssh -p 1212 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=no" --delete --progress build-result/$DIST jenkins@impera.io:/srv/www/impera/repo/
