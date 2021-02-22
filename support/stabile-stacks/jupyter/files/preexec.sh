#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Disable data image - this stack does not really need a data image
perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab

