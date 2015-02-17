#!/bin/bash -xe

TDIR=/tmp/build
REPO=$2
TARGET=$3
TAG=""

echo "Checking out code"
git clone $REPO impera
cd impera
if [[ $TARGET == "latest" ]]; then
	git checkout -b $(git tag | sort -n -r | head -n 1)
elif [[ $TARGET == "dev" ]]; then
	# actuall do nothing :)
	echo "Using dev"
	TAG=$(date +%Y%m%d%H%M)
else
	echo "No build target given!" >&2
	exit 1
fi

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

rpmbuild -D "tag $TAG" -D "%_topdir $TDIR/rpmbuild" -bs $TDIR/rpmbuild/SPECS/impera.spec

echo "Building RPM"
rpmbuild -D "tag $TAG" -D "%_topdir $TDIR/rpmbuild" --rebuild $TDIR/rpmbuild/SRPMS/*.rpm

cp $TDIR/rpmbuild/SRPMS/*.rpm $1 || exit 1
cp $TDIR/rpmbuild/RPMS/noarch/*.rpm $1 || exit 1

cd /code
cat deps | while read DIR REPO; do
    cd /code
    rm -rf $DIR
    git clone $REPO $DIR
    cd $DIR
    if [[ -e fedora.sh ]]; then
        bash fedora.sh $1 || exit 1
    fi
done

cd /code
rm -rf $TDIR/rpmbuild
