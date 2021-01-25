#!/bin/sh

steamExec backupallimages
steamExec unmountallimages
steamExec backupengine

# Sometimes this file gets corrupted for no apparent reason. This among other things prevents node backups from running. Uncomment this ugly fix is to regularly rewrite it

#echo "irigo ALL=NOPASSWD: ALL
#Defaults:irigo !requiretty" > /mnt/stabile/tftp/bionic/live/filesystem.dir/etc/sudoers.d/stabile
