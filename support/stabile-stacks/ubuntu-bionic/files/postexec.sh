#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Install Webmin
bash -c 'echo "deb http://download.webmin.com/download/repository sarge contrib" >> /etc/apt/sources.list'
wget http://www.webmin.com/jcameron-key.asc
apt-key add jcameron-key.asc
# DEBIAN_FRONTEND=noninteractive dpkg --configure -a
apt-get update
>&2 echo "Installing Webmin"
#DEBIAN_FRONTEND=noninteractive dpkg -i /tmp/files/webmin_1.953_all.deb
DEBIAN_FRONTEND=noninteractive apt-get -q -y install webmin
>&2 echo "Done"

# Install webmin module
# Include all the modules we want installed for this app
cd /tmp/files/
tar cvf $dname.wbm.tar --exclude=stabile/tabs/* stabile
tar rvf $dname.wbm.tar stabile/tabs/commands stabile/tabs/security stabile/tabs/servers stabile/tabs/storage
mv $dname.wbm.tar $dname.wbm
gzip -f $dname.wbm
cp -a $dname.wbm.gz /tmp/stabile.wbm.gz
bash -c '/usr/share/webmin/install-module.pl /tmp/stabile.wbm.gz'

# Simple script to register this server with admin webmin server when webmin starts
# This script is also responsible for mounting nfs-share, copy back data, etc. if upgrading/reinstalling
cp /tmp/files/stabile-ubuntu.pl /usr/local/bin
cp /tmp/files/stabile-ubuntu-networking.pl /usr/local/bin
chmod 755 /usr/local/bin/stabile-ubuntu.pl
chmod 755 /usr/local/bin/stabile-ubuntu-networking.pl
ln -s /usr/local/bin/stabile-ubuntu.pl /usr/local/bin/stabile-helper
ln -s /usr/local/bin/stabile-ubuntu-networking.pl /usr/local/bin/stabile-networking
bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Origo Stabile
Wants=network-online.target
After=stabile-networking.service
After=network.target network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-ubuntu.pl
TimeoutSec=60
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-ubuntu.service'
chmod 664 /etc/systemd/system/stabile-ubuntu.service

# Zap existing file
> /etc/network/interfaces
bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Setup network for Origo Stabile
Wants=network-online.target
After=network.target network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-networking
TimeoutSec=0
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-networking.service'
chmod 664 /etc/systemd/system/stabile-networking.service
systemctl enable stabile-networking

systemctl daemon-reload
systemctl enable stabile-networking.service
systemctl enable stabile-shellinabox.service
systemctl enable stabile-ubuntu.service

# Set up SSL access to Webmin on port 10001
cp /etc/apache2/sites-available/default-ssl.conf /etc/apache2/sites-available/webmin-ssl.conf
perl -pi -e 's/<VirtualHost _default_:443>/<VirtualHost _default_:10001>/;' /etc/apache2/sites-available/webmin-ssl.conf
perl -pi -e 's/(<\/VirtualHost>)/    ProxyPass \/ http:\/\/127.0.0.1:10000\/\n            ProxyPassReverse \/ http:\/\/127.0.0.1:10000\/\n$1/;' /etc/apache2/sites-available/webmin-ssl.conf
perl -pi -e 's/(DocumentRoot \/var\/www\/html)/$1\n        <Location \/>\n            deny from all\n            allow from 10.0.0.0\/8 #stabile\n        <\/Location>/;' /etc/apache2/sites-available/webmin-ssl.conf
perl -pi -e 's/Listen 443/Listen 443\n    Listen 10001/;' /etc/apache2/ports.conf

perl -pi -e 's/ssl=1/ssl=0/;' /etc/webmin/miniserv.conf
perl -pi -e 's/referers_none=1/referers_none=0\nreferers=127.0.0.1\nreferer=1/;' /etc/webmin/config
echo "anonymous=/stabile=stabile" >> /etc/webmin/miniserv.conf
echo "stabile:x:0" >> /etc/webmin/miniserv.users
echo "admin:x:0" >> /etc/webmin/miniserv.users
echo "stabile: *" >> /etc/webmin/webmin.acl
echo "admin: *" >> /etc/webmin/webmin.acl
echo "rpc=1" >> /etc/webmin/stabile.acl
chmod 640 /etc/webmin/stabile.acl

# Disable ondemand CPU-scaling service
update-rc.d ondemand disable

# Disable gzip compression in Apache (enable it manually if desired)
a2dismod -f deflate

# Enable SSL
a2enmod ssl
a2ensite default-ssl
a2ensite webmin-ssl

# Enable mod_proxy
a2enmod proxy
a2enmod proxy_http

# Disable ssh login from outside - reenable from configuration UI
bash -c 'echo "sshd: ALL" >> /etc/hosts.deny'
bash -c 'echo "sshd: 10.0.0.0/8 #stabile" >> /etc/hosts.allow'
bash -c 'echo "AllowUsers *@10.0.0.0/8 #stabile" >> /etc/ssh/sshd_config'
perl -pi -e 's/PasswordAuthentication .+/PasswordAuthentication yes/g;' /etc/ssh/sshd_config

# Generate ssh host keys
# ssh-keygen -A

# Disable Webmin login from outside - reenable from configuration UI
bash -c 'echo "allow=10.0.0.0/8 127.0.0.0/16" >> /etc/webmin/miniserv.conf'

# Set nice color xterm as default
bash -c 'echo "export TERM=xterm-color" >> /etc/bash.bashrc'
perl -pi -e 's/PS1="/# PS1="/' /home/stabile/.bashrc
perl -pi -e 's/PS1="/# PS1="/' /root/.bashrc

# Disable Netplan
systemctl unmask networking
systemctl enable networking
systemctl disable systemd-networkd.socket systemd-networkd networkd-dispatcher systemd-networkd-wait-online
systemctl mask systemd-networkd.socket systemd-networkd networkd-dispatcher systemd-networkd-wait-online

# Clean up
rm -r /tmp/files