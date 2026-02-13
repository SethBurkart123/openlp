#!/bin/bash
###############################################################################
# PPA Build Script for OpenLP                                                 #
###############################################################################

OPENLP_VERSION=$1
RELEASE_NAME=$2
PROJECT_DIR=$HOME/Projects/OpenLP
UPLOADS_DIR=$PROJECT_DIR/Uploads
PACKAGING_DIR=$HOME/Packaging
UBUNTU_DIR=$PACKAGING_DIR/debian-package
TARGT_TARBALL=$PACKAGING_DIR/Tarballs/openlp_${OPENLP_VERSION}.orig.tar.gz

export DEBFULLNAME="Raoul Snyman"
export DEBEMAIL="raoul@snyman.info"

echo -n "Copying source tarball..."
cd $UPLOADS_DIR
if [[ ! -f "$UPLOADS_DIR/OpenLP-${OPENLP_VERSION}.tar.gz" ]]; then
	echo "$UPLOADS_DIR/OpenLP-${OPENLP_VERSION}.tar.gz NOT FOUND, exiting."
	exit 1
fi
cp $UPLOADS_DIR/OpenLP-${OPENLP_VERSION}.tar.gz $TARGT_TARBALL
echo done.
echo -n "Backing up changelog..."
cd $UBUNTU_DIR
cp $UBUNTU_DIR/debian/changelog $PACKAGING_DIR/changelog.bak
echo done.
echo "Building package..."
dch --force-distribution -D $RELEASE_NAME -v $OPENLP_VERSION-0ubuntu1~${RELEASE_NAME}1 Autobuild
bzr bd --builder='debuild -S -m"Raoul Snyman <raoulsnyman@openlp.org>"' --orig-dir="$PACKAGING_DIR/Tarballs" --build-dir="$PACKAGING_DIR/Builds"
if [[ $? -ne 0 ]]; then
	echo "Failed to build package, exiting..."
	exit 1
fi
echo "Uploading package source..."
cd $PACKAGING_DIR/Builds
dput openlp-dev openlp_$OPENLP_VERSION-0ubuntu1~${RELEASE_NAME}1_source.changes
echo -n "Removing generated files..."
rm $PACKAGING_DIR/Tarballs/*
rm -r $PACKAGING_DIR/Builds/*
echo done.
echo -n "Restoring changelog..."
cd $UBUNTU_DIR
cp $PACKAGING_DIR/changelog.bak $UBUNTU_DIR/debian/changelog
echo "done."
