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

if [ "${BUILDTYPE}x" == "x" ]; then
    $BUILDTYPE=windows
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
    /home/openlp/bin/openlp_tweeter.py openlp_dev "Latest $PLATFORM development build of OpenLP 2.0 available at http://openlp.org/files/latest$EXT - version ${BASH_REMATCH[2]} build ${BASH_REMATCH[4]}."
    if [ $? -ne 0 ]; then
        exit 4
    fi
fi

