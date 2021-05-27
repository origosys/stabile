#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Install getssl
curl --silent https://raw.githubusercontent.com/srvrco/getssl/master/getssl > /usr/local/bin/getssl
chmod 711 /usr/local/bin/getssl

# Install webmin module
# Include all the modules we want installed for this app
cd /tmp/files/
tar cf $dname.wbm.tar --exclude=stabile/tabs/* stabile
tar rf $dname.wbm.tar stabile/tabs/commands stabile/tabs/security stabile/tabs/servers stabile/tabs/storage
mv $dname.wbm.tar $dname.wbm
gzip -f $dname.wbm
cp -a $dname.wbm.gz /tmp/stabile.wbm.gz
bash -c '/usr/libexec/webmin/install-module.pl /tmp/stabile.wbm.gz'

# Simple script to register this server with admin webmin server when webmin starts
# This script is also responsible for mounting nfs-share, copy back data, etc. if upgrading/reinstalling
cp /tmp/files/stabile-centos.pl /usr/local/bin
cp /tmp/files/stabile-centos-networking.pl /usr/local/bin
chmod 755 /usr/local/bin/stabile-centos.pl
chmod 755 /usr/local/bin/stabile-centos-networking.pl
ln -s /usr/local/bin/stabile-centos.pl /usr/local/bin/stabile-helper
ln -s /usr/local/bin/stabile-centos-networking.pl /usr/local/bin/stabile-networking
bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Origo Stabile
Wants=network-online.target
After=stabile-networking.service
After=webmin.service
After=network.target network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-centos.pl
TimeoutSec=60
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-centos.service'
chmod 664 /etc/systemd/system/stabile-centos.service
systemctl enable stabile-centos

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Networking script for Origo Stabile
Before=network-pre.target
Wants=network-pre.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-networking
TimeoutSec=60
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-networking.service'
chmod 664 /etc/systemd/system/stabile-networking.service
systemctl enable stabile-networking

# Set up SSL access to Webmin on port 10001
cp /etc/httpd/conf.d/ssl.conf /etc/httpd/conf.d/webmin-ssl.conf
perl -pi -e 's/<VirtualHost _default_:443>/<VirtualHost _default_:10001>/;' /etc/httpd/conf.d/webmin-ssl.conf
perl -pi -e 's/(<\/VirtualHost>)/    ProxyPass \/ http:\/\/127.0.0.1:10000\/\n    ProxyPassReverse \/ http:\/\/127.0.0.1:10000\/\n$1/;' /etc/httpd/conf.d/webmin-ssl.conf
perl -pi -e 's/(DocumentRoot "\/var\/www\/html")/$1\n        <Location \/>\n            deny from all\n            allow from 10.0.0.0\/8 #stabile\n        <\/Location>/;' /etc/httpd/conf.d/webmin-ssl.conf
perl -pi -e 's/Listen 443/Listen 10001/;' /etc/httpd/conf.d/webmin-ssl.conf

perl -pi -e 's/ssl=1/ssl=0/;' /etc/webmin/miniserv.conf
perl -pi -e 's/referers_none=1/referers_none=0\nreferers=127.0.0.1\nreferer=1/;' /etc/webmin/config
echo "anonymous=/stabile=stabile" >> /etc/webmin/miniserv.conf
echo "stabile:x:0" >> /etc/webmin/miniserv.users
echo "admin:x:0" >> /etc/webmin/miniserv.users
echo "stabile: *" >> /etc/webmin/webmin.acl
echo "admin: *" >> /etc/webmin/webmin.acl
echo "rpc=1" >> /etc/webmin/stabile.acl
chmod 640 /etc/webmin/stabile.acl

# Disable gzip compression in Apache (enable it manually if desired)
perl -pi -e 's/(LoadModule deflate_module)/\#$1/;' /etc/httpd/conf.modules.d/00-base.conf

# Disable ssh login from outside - reenable from configuration UI
bash -c 'echo "sshd: ALL" >> /etc/hosts.deny'
bash -c 'echo "sshd: 10.0.0.0/8 #stabile" >> /etc/hosts.allow'
bash -c 'echo "AllowUsers *@10.0.0.0/8 #stabile" >> /etc/ssh/sshd_config'
perl -pi -e 's/PasswordAuthentication .+/PasswordAuthentication yes/g;' /etc/ssh/sshd_config

# Generate ssh host keys
ssh-keygen -A

# Disable Webmin login from outside - reenable from configuration UI
bash -c 'echo "allow=10.0.0.0/8 127.0.0.0/16" >> /etc/webmin/miniserv.conf'

# Give stabile user sudo rights
echo "stabile ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/stabile

# Disable selinux to Work around SELinux bug with systemd https://major.io/2015/09/18/systemd-in-fedora-22-failed-to-restart-service-access-denied
#setenforce 0
perl -pi -e 's/SELINUX=enforcing/SELINUX=disabled/;' /etc/selinux/config
perl -pi -e 's/SELINUXTYPE=targeted/SELINUX=minimum/;' /etc/selinux/config

# Set nice color xterm as default
bash -c 'echo "export TERM=xterm-color" >> /etc/bash.bashrc'
perl -pi -e 's/PS1="/# PS1="/' /home/stabile/.bashrc
perl -pi -e 's/PS1="/# PS1="/' /root/.bashrc

# Disable firewalld - we use iptables manually
systemctl disable firewalld
# Enable Centos web UI on port 9090
# systemctl enable cockpit.socket
# Enable Apache
systemctl enable httpd

# Clean up
rm -r /tmp/files