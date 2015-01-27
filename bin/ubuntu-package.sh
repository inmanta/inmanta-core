#!/bin/bash -xe

TDIR=/tmp/build
rm -rf $TDIR
mkdir -p $TDIR

echo "Checking out latest tag"
git clone https://github.com/impera-io/impera
cd impera
git checkout -b $(git tag | sort -n -r | head -n 1)

echo "Creating a source distribution"
rm -rf dist
python3 setup.py sdist

echo "Building deb package"
FILE=dist/impera*
ORIG_FILE=$(basename $FILE | sed "s/impera-\([0-9.]*\).tar.gz/impera_\1.orig.tar.gz/g")
cp $FILE $TDIR/$ORIG_FILE
cp -a debian $TDIR
cd $TDIR

tar xvfz $ORIG_FILE
mv debian impera-*/

cd impera-*

debuild -i -uc -us

cp $TDIR/* $1

cd /code
cat deps | while read DIR REPO; do
    cd /code
    rm -rf $DIR
    git clone $REPO $DIR
    cd $DIR
    [[ -e ubuntu.sh ]] && bash ubuntu.sh $1
done
cd /code

cd $1
dpkg-scanpackages . | gzip > $1/Packages.gz

rm -rf $TDIR

