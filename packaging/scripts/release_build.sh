#!/bin/bash

VERSION=$1
RELEASE=release-$VERSION
FILENAME=OpenLP-$VERSION.tar.gz
#TSDIR=$RELEASE/resources/i18n
#QMDIR=$RELEASE/openlp/i18n

echo Starting the OpenLP 2.0 Release Build Script
echo --------------------------------------------
echo -ne "Updating trunk-2.0...\r"
cd /home/openlp/Projects/OpenLP/trunk-2.0
bzr update -q
echo "Updating trunk-2.0...done."
echo -ne "Branching release tag...\r"
cd /home/openlp/Projects/OpenLP
bzr branch trunk-2.0 $RELEASE -r tag:$VERSION -q
echo "Branching release tag...done."
echo -n "Creating source distribution..."
cd /home/openlp/Projects/OpenLP/$RELEASE
python setup.py sdist
echo "done."
#echo -n "Updating Version File..."
#echo "$VERSION" > version.txt
#scp version.txt openlp@openlp.org:public_html/files/version.txt
#rm version.txt
echo "Building sources for PPA..."
~/bin/build_release_deb.sh $VERSION utopic
echo -n "Cleaning up..."
cd /home/openlp/Projects/OpenLP
rm -fR $RELEASE
echo "done."
echo --------------------------------------------
echo Finished OpenLP 2.0 Release Build Script
