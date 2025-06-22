#!/bin/bash
###############################################################################
# Debian Build Script for OpenLP                                              #
###############################################################################
DEB_VERSION=$1
RELEASE_NAME=$2
export RELEASE_NAME
ROOT_DIR=~/Projects/OpenLP
SDIST_TARBALL=$ROOT_DIR/release-${DEB_VERSION}/dist/OpenLP-$DEB_VERSION.tar.gz
TARGT_TARBALL=$ROOT_DIR/tarballs/openlp_$DEB_VERSION.orig.tar.gz
echo "Copying $SDIST_TARBALL to $TARGT_TARBALL"
cp $SDIST_TARBALL $TARGT_TARBALL
cd $ROOT_DIR/debian-package
dch --force-distribution -D $RELEASE_NAME -v $DEB_VERSION-0ubuntu1~${RELEASE_NAME}1 Autobuild -b
bzr bd --builder='debuild -S -sa -m"Raoul Snyman <raoul.snyman@saturnlaboratories.co.za>"' --orig-dir="$ROOT_DIR/tarballs"
cd $ROOT_DIR/build-area
dput openlp-release openlp_$DEB_VERSION-0ubuntu1~${RELEASE_NAME}1_source.changes
cd $ROOT_DIR/debian-package
bzr revert
