#!/bin/bash

if [ $# -lt 2 ]
then
  echo "Usage: `basename $0` {filename} {windows|osx|portable} [delete]"
  exit 5
fi

FILENAME=$1
BASEFILE=`basename $FILENAME`
BUILDTYPE=$2
REGEX='(OpenLP-|OpenLPPortable_)([0-9]\.[0-9]\.[0-9]+)(-bzr|\.)([0-9]+)[.|-]'

if [ $# -eq 3 -a "$3" == "delete" ]; then
    AUTODELETE=1
else
    AUTODELETE=0
fi

if [ ! -f $FILENAME ]; then
    echo "$FILENAME does not exist, exiting."
    exit 1
fi
if [ "${BUILDTYPE}x" == "x" ]; then
    $BUILDTYPE=windows
fi
echo "Uploading file..."
scp $FILENAME openlp@openlp.org:public_html/files/
if [ $? -ne 0 ]; then
    echo "Failed to upload ${FILENAME}."
    exit 2
fi
echo "Updating build information on server..."
ssh openlp@openlp.org "python update_builds.py $BUILDTYPE $BASEFILE"
if [ $? -ne 0 ]; then
    echo "Failed to update build ${BUILDTYPE} ${BASEFILE}."
    exit 3
fi
if [ $AUTODELETE -eq 1 ]; then
    rm $FILENAME
fi
if [[ $BASEFILE =~ $REGEX ]]; then
    if [ "$BUILDTYPE" == "windows" ]; then
        PLATFORM="Windows"
        EXT=".exe"
    elif [ "$BUILDTYPE" == "macos" ]; then
        PLATFORM="macOS"
        EXT=".dmg"
    elif [ "$BUILDTYPE" == "portable" ]; then
        PLATFORM="PortableApps"
        EXT="-portable.exe"
    fi
    echo "Notifying Twitter..."
    /home/openlp/bin/openlp_tweeter.py openlp_dev "Latest $PLATFORM development build of OpenLP 2.2 available at http://openlp.org/files/latest$EXT - version ${BASH_REMATCH[2]} build ${BASH_REMATCH[4]}."
    if [ $? -ne 0 ]; then
        exit 4
    fi
fi

