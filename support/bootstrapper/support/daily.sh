#!/bin/sh

steamExec backupallimages
steamExec unmountallimages
steamExec backupengine

# This file regularly gets corrupted for no apparent reason. This among other things prevents node backups from running. Ugly fix is to regularly rewrite it
echo "irigo ALL=NOPASSWD: ALL
Defaults:irigo !requiretty" > /mnt/stabile/tftp/lucid/live/filesystem.dir/etc/sudoers.d/stabile