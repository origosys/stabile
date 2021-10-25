#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Disable data image - this stack does not really need a data image
perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab

# Utility script for setting up discourse to work with this stack
cp /tmp/files/stabile-discourse.pl /usr/local/bin
chmod 755 $1/usr/local/bin/stabile-discourse.pl

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile discourse
Wants=network-online.target redis-server.service stabile-ubuntu.service webmin.service
After=stabile-networking.service remote-fs.target nss-lookup.target apache2.service redis-server.service stabile-ubuntu.service webmin.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-discourse.pl
TimeoutSec=1800
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-discourse.service'
chmod 664 /etc/systemd/system/stabile-discourse.service

systemctl enable stabile-discourse.service

