#!/bin/bash

FILENAME=`date +%Y%m%d-%H%M%S`.rss
BACKUPDIR=~/georss
BACKUPDAYS=14

# Delete files older than $BACKUPDAYS days ago
find $BACKUPDIR -mtime $BACKUPDAYS -exec rm -f {} \;

# Get the latest GeoRSS from our map
wget -c -O $BACKUPDIR/$FILENAME 'http://maps.google.com/maps/ms?ie=UTF8&source=embed&msa=0&output=georss&msid=113314234297482809599.00047e88b1985e07ad495'

