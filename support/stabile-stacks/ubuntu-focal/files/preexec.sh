#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Change fstab since we are using virtio
perl -pi -e "s/sda/vda/g;" /etc/fstab

# Simple script to start shellinabox
bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Shellinabox for Origo Stabile

[Service]
ExecStart=/usr/share/webmin/stabile/shellinabox/shellinaboxd -b -t -n --no-beep --static-file=favicon.ico:/usr/share/webmin/stabile/images/icons/favicon.ico --static-file=ShellInABox.js:/usr/share/webmin/stabile/shellinabox/ShellInABox.js
TimeoutSec=15
RemainAfterExit=yes
Type=forking

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-shellinabox.service'
chmod 664 /etc/systemd/system/stabile-shellinabox.service
systemctl enable stabile-shellinabox.service

# For debugging - remove before release
#echo "stabile:stabile" | chpasswd
# Add to sudoers
usermod -aG sudo stabile
# Empty passwords and disable login
passwd -d stabile
passwd -l stabile
passwd -d root
passwd -l root

# Mount data disk
mkdir /mnt/data
echo "/dev/vdb1       /mnt/data       ext4    noatime 0       0" >> /etc/fstab

# Set hostname
echo ubuntu-focal > /etc/hostname