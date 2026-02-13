#!/bin/bash
###############################################################################
# Nightly Build Script for OpenLP                                             #
###############################################################################

REGEX='OpenLP-([0-9]\.[0-9]\.[0-9])-bzr([0-9]+)[.|-]'
PROJECT_DIR=/home/openlp/Projects/OpenLP
SOURCE_DIR=$PROJECT_DIR/trunk
VERSION_FILE=$SOURCE_DIR/openlp/.version
PACKAGING_DIR=/home/openlp/Packaging
UPLOADS_DIR=$PROJECT_DIR/Uploads

echo Starting the OpenLP 2.2 Nightly Build Script
echo --------------------------------------------
echo -ne "Updating code...\r"
cd $SOURCE_DIR
bzr update -q
echo "Updating code...done."

# We can't get the version number until after updating the code
# otherwise the version number we get is out-of-date
OPENLP_VERSION=`~/bin/openlp_version.py $SOURCE_DIR`
UPLOAD_TARBALL=OpenLP-${OPENLP_VERSION}.tar.gz
PACKAGE_TARBALL=$PACKAGING_DIR/Tarballs/openlp_${OPENLP_VERSION}.orig.tar.gz

echo -n "Checking revision..."
if [[ -f "$VERSION_FILE" && "`bzr revno`" -eq "`cat $VERSION_FILE`" ]]; then
    echo done.
    echo OpenLP is already at the latest revision, aborting build.
    echo --------------------------------------------
    echo Finished OpenLP 2.2 Nightly Build Script
    exit
fi
echo done.
echo -n "Writing version number..."
bzr revno > $VERSION_FILE
echo done.
echo -n "Exporting source for $OPENLP_VERSION ..."
if [[ -d "../OpenLP-$OPENLP_VERSION" ]]; then
	rm -r ../OpenLP-$OPENLP_VERSION
fi
bzr export ../OpenLP-$OPENLP_VERSION
echo done.
echo -n "Creating source tarball $UPLOADS_DIR/$UPLOAD_TARBALL ..."
cd $PROJECT_DIR
tar -czf $UPLOADS_DIR/$UPLOAD_TARBALL OpenLP-$OPENLP_VERSION
echo done.
echo -n "Uploading tarball to download location..."
cd $UPLOADS_DIR
scp -q $UPLOADS_DIR/$UPLOAD_TARBALL openlp@openlp.org:public_html/files/
ssh -q openlp@openlp.org "python update_builds.py source $UPLOAD_TARBALL"
echo done.
echo -n "Updating Version File..."
echo "$VERSION" > nightly_version.txt
scp -q nightly_version.txt openlp@openlp.org:public_html/files/nightly_version.txt
rm nightly_version.txt
echo done.
echo -n "Notifying Twitter..."
if [[ $UPLOAD_TARBALL =~ $REGEX ]]; then
        VERSION_STRING="version ${BASH_REMATCH[1]}, build ${BASH_REMATCH[2]}"
else
	VERSION_STRING="version ${OPENLP_VERSION}"
fi
~/bin/openlp_tweeter.py openlp_dev "Latest nightly source tarball of OpenLP 2.2 available at http://openlp.org/files/latest.tar.gz - ${VERSION_STRING}."
echo done.
echo Building sources for PPA...
~/bin/build_nightly_deb.sh trusty
~/bin/build_nightly_deb.sh utopic
~/bin/build_nightly_deb.sh vivid
echo -n "Notifying Twitter..."
~/bin/openlp_tweeter.py openlp_dev "Latest Ubuntu nightly package of OpenLP 2.2 queued for building in the Nightly PPA (ppa:openlp-core/nightly) - ${VERSION_STRING}."
echo done.
echo -n "Cleaning up..."
rm -r $UPLOADS_DIR/*
rm $PACKAGE_TARBALL
echo done.
echo --------------------------------------------
echo Finished OpenLP 2.2 Nightly Build Script
