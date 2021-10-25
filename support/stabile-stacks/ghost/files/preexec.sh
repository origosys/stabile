#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Disable data image - this stack does not really need a data image
perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab

# Utility script for setting up ghost to work with this stack
cp /tmp/files/stabile-ghost.pl /usr/local/bin
chmod 755 /usr/local/bin/stabile-ghost.pl

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile ghost
Wants=network-online.target
After=stabile-networking.service remote-fs.target nss-lookup.target apache2.service

[Service]
Type=simple
ExecStart=/usr/local/bin/stabile-ghost.pl
TimeoutSec=120
#WorkingDirectory=/var/www/ghost
#User=999
#Environment="NODE_ENV=production"
Restart=always

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-ghost.service'
chmod 664 /etc/systemd/system/stabile-ghost.service

systemctl enable stabile-ghost.service

# For debugging - remove before release
# echo "stabile:stabile" | chpasswd
