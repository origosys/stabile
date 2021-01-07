#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Disable data image - this stack does not really need a data image
perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab

# For debugging - allows ssh login from admin server. Remove before release.
# echo "stabile:stabile" | chpasswd
