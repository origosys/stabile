#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Disable data image - this stack does not really need a data image
# perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab

# For debugging - allows ssh login from admin server. Remove before release.
# echo "stabile:stabile" | chpasswd

# Add MongoDB repo
curl -fsSL https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list

# Utility script for setting up MongoDB to work with this stack
cp /tmp/files/stabile-mongodb.pl /usr/local/bin
chmod 755 $1/usr/local/bin/stabile-mongodb.pl

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile MongoDB
Wants=network-online.target
After=mongod.service
After=stabile-networking.service
After=network.target network-online.target
After=stabile-ubuntu.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-mongodb.pl
TimeoutSec=500
RemainAfterExit=yes
Environment="HOME=/root"

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-mongodb.service'
chmod 664 /etc/systemd/system/stabile-mongodb.service
