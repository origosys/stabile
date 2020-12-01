#!/usr/bin/env bash
DOJO="dojo-release-1.7.2"
DOJO_SRC="$DOJO-src"

DOJO_BUNDLE="$DOJO.tar.gz"
DOJO_URL="http://download.dojotoolkit.org/release-1.7.2/$DOJO_BUNDLE"

DOJO_SRC_BUNDLE="$DOJO-src.tar.gz"
DOJO_SRC_URL="http://download.dojotoolkit.org/release-1.7.2/$DOJO_SRC_BUNDLE"

if ! test -e "static/js/$DOJO"; then
   echo "Fetching $DOJO"
   cd static/js
   wget $DOJO_URL
   tar xfv $DOJO_BUNDLE
   ln -s $DOJO/dojo dojo
   ln -s $DOJO/dojox dojox
   ln -s $DOJO/dijit dijit
   rm $DOJO_BUNDLE
   cd ../..
else
   echo "$DOJO aldready present"
fi

if ! test -e "static/js/$DOJO_SRC"; then
   echo "Fetching $DOJO_SRC_BUNDLE"
   cd static/js
   wget $DOJO_SRC_URL
   tar xfv $DOJO_SRC_BUNDLE
   ln -s $DOJO_SRC/util/ util
   rm $DOJO_SRC_BUNDLE
   cd ../..
else
   echo "$DOJO_SRC aldready present"
fi

