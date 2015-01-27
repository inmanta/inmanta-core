#!/bin/bash -xe

TDIR=/tmp/build

echo "Checking out latest tag"
git clone https://github.com/impera-io/impera
cd impera
git checkout -b $(git tag | sort -n -r | head -n 1)

echo "Creating a source distribution"
rm -rf dist
python3 setup.py sdist

echo "Building SRPM"
rm -rf $TDIR
mkdir -p $TDIR
HOME=$TDIR rpmdev-setuptree
sed -i "s/\%(echo \$HOME)/\/tmp\/build/g" $TDIR/.rpmmacros

cp dist/impera-*.tar.gz $TDIR/rpmbuild/SOURCES/
cp impera.spec $TDIR/rpmbuild/SPECS/impera.spec

rpmbuild -D "%_topdir $TDIR/rpmbuild" -bs $TDIR/rpmbuild/SPECS/impera.spec

echo "Building RPM"
rpmbuild -D "%_topdir $TDIR/rpmbuild" --rebuild $TDIR/rpmbuild/SRPMS/*.rpm

cp $TDIR/rpmbuild/SRPMS/*.rpm $1
cp $TDIR/rpmbuild/RPMS/noarch/*.rpm $1

cd /code
cat deps | while read DIR REPO; do
    cd /code
    rm -rf $DIR
    git clone $REPO $DIR
    cd $DIR
    [[ -e fedora.sh ]] && bash fedora.sh $1
done

cd /code
createrepo $1

rm -rf $TDIR/rpmbuild
