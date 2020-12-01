#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# The CentOS image does not have /dev/null, which is needed for yum
mknod /dev/null c 1 3
chmod 666 /dev/null

# Enable PowerTools
yum config-manager --set-enabled PowerTools

# Install Perl + Webmin
yum -y install epel-release
# yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
yum -y install tar certbot python3-certbot-apache jq cloud-utils-growpart net-tools
yum -y install perl perl-CPAN perl-Net-SSLeay openssl perl-Encode-Detect
yum -y install perl-IO-Tty perl-String-ShellQuote perl-JSON perl-Authen-PAM
yum -y install /tmp/files/webmin-1.941-1.noarch.rpm

# perl -MCPAN -e 'install URI::Encode'
cpan install URI::Encode <<<yes

# Simple script to start shellinabox
bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Shellinabox for Origo Stabile

[Service]
ExecStart=/usr/libexec/webmin/stabile/tabs/servers/shellinaboxd -b -t -n --no-beep --static-file=favicon.ico:/usr/share/webmin/stabile/images/icons/favicon.ico --static-file=ShellInABox.js:/usr/libexec/webmin/stabile/tabs/servers/ShellInABox.js
TimeoutSec=15
RemainAfterExit=yes
Type=forking

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-shellinabox.service'
chmod 664 /etc/systemd/system/stabile-shellinabox.service
systemctl enable stabile-shellinabox.service

# Install getssl
curl --silent https://raw.githubusercontent.com/srvrco/getssl/master/getssl > /usr/local/bin/getssl
chmod 711 /usr/local/bin/getssl

# For debugging - remove before release
#echo "stabile:stabile" | chpasswd
# Add to sudoers
usermod -aG sudo stabile
# Empty passwords and disable login
passwd -d stabile
passwd -l stabile
passwd -d root
#passwd -l root

# Mount data disk
mkdir /mnt/data
echo "/dev/vdb1       /mnt/data       ext4    noatime 0       0" >> /etc/fstab

# Set hostname
echo centos-8 > /etc/hostname