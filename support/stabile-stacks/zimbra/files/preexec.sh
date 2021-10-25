#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Mount data image on /opt/zimbra
perl -pi -e 's/(\/dev\/vdb1.+)\/mnt\/data(.+)/$1\/opt\/zimbra$2/;' /etc/fstab

# Utility script for setting up zimbra to work with this stack
cp /tmp/files/stabile-zimbra.pl /usr/local/bin
chmod 755 /usr/local/bin/stabile-zimbra.pl

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile zimbra
Wants=network-online.target
After=stabile-networking.service remote-fs.target nss-lookup.target apache2.service zimbra.service

[Service]
Type=simple
ExecStart=/usr/local/bin/stabile-zimbra.pl
TimeoutSec=120
#WorkingDirectory=/var/www/zimbra
#User=999
#Environment="NODE_ENV=production"
#Restart=always

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-zimbra.service'
chmod 664 /etc/systemd/system/stabile-zimbra.service

systemctl enable stabile-zimbra.service

# Ugly hack to make getssl reload Zimbra instead of Apache
perl -pi -e 's/RELOAD_CMD=.*/RELOAD_CMD="\/usr\/local\/bin\/stabile-zimbra.pl updatecerts"/' /usr/local/bin/stabile-ubuntu.pl

# Allow zimbra to connect to localhost with user zimbra
perl -pi -e 's/sshd:/sshd: 127.0.0.1/;' /etc/hosts.allow
perl -pi -e 's/AllowUsers /AllowUsers *@127.0.0.1 /;' /etc/hosts.allow

# Directory for listing Zimbra dns entries
mkdir /var/www/html/dns

mkdir /root/.getssl
echo 'PREFERRED_CHAIN="ISRG Root X1"
FULL_CHAIN_INCLUDE_ROOT="true"' >> /root/.getssl/getssl.cfg

# Bump up timeout because getssl reloads Zimbra
sed -i "s/TimeoutSec=60/TimeoutSec=600/"  /etc/systemd/system/stabile-ubuntu.service

# For debugging - remove before release
echo "stabile:stabile" | chpasswd
