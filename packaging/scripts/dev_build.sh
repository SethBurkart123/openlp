#!/bin/bash

VERSION=$1
PROJECTS_DIR=/home/openlp/Projects
SOURCE_DIR=$PROJECTS_DIR/OpenLP/trunk
RELEASE_DIR=release-$VERSION
UPLOADS_DIR=/home/openlp/Projects/OpenLP/Uploads
FILENAME=OpenLP-$VERSION.tar.gz
#TSDIR=$RELEASE/resources/i18n
#QMDIR=$RELEASE/openlp/i18n

echo Starting the OpenLP Development Build Script
echo --------------------------------------------
echo -ne "Updating trunk...\r"
cd $SOURCE_DIR
bzr update -q
echo "Updating trunk...done."
echo -ne "Branching release tag (${VERSION})...\r"
cd ..
bzr branch trunk $RELEASE_DIR -r tag:$VERSION -q
echo "Branching release tag (${VERSION})...done."
echo -n "Creating source distribution..."
cd /home/openlp/Projects/OpenLP/$RELEASE_DIR
python setup.py sdist
echo "done."
echo -n "Copying release tarball..."
cp dist/$FILENAME $UPLOADS_DIR/
echo "done."
echo -n "Updating Version File..."
echo "$VERSION" > dev_version.txt
scp dev_version.txt openlp@openlp.org:public_html/files/dev_version.txt
rm dev_version.txt
echo "Building sources for PPA..."
~/bin/build_dev_deb.sh $VERSION trusty
~/bin/build_dev_deb.sh $VERSION utopic
~/bin/build_dev_deb.sh $VERSION vivid
echo -n "Cleaning up..."
cd /home/openlp/Projects/OpenLP
rm -r $RELEASE_DIR
echo "done."
echo --------------------------------------------
echo Finished the OpenLP Development Build Script
