#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Disable data image - this stack does not really need a data image
perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab

# Utility script for setting up rocketchat to work with this stack
cp /tmp/files/stabile-rocketchat.pl /usr/local/bin
chmod 755 /usr/local/bin/stabile-rocketchat.pl

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile rocketchat
Wants=network-online.target
After=stabile-networking.service remote-fs.target nss-lookup.target apache2.service mongod.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-rocketchat.pl
TimeoutSec=600
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-rocketchat.service'
chmod 664 /etc/systemd/system/stabile-rocketchat.service

systemctl enable stabile-rocketchat.service

# For debugging - remove before release
# echo "stabile:stabile" | chpasswd
