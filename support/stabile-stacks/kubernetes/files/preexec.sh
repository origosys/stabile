#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Disable data image - this stack does not really need a data image
perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab
# Disable swap
perl -pi -e 's/(\/swapfile.+)/#$1/;' /etc/fstab

curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" > /etc/apt/sources.list.d/kubernetes.list

curl -s https://baltocdn.com/helm/signing.asc | sudo apt-key add -
echo "deb https://baltocdn.com/helm/stable/debian/ all main" > /etc/apt/sources.list.d/helm-stable-debian.list

# Utility script for setting up Kubernetes to work with this stack
cp /tmp/files/stabile-kubernetes.pl /usr/local/bin
chmod 755 $1/usr/local/bin/stabile-kubernetes.pl

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile Kubernetes
Wants=network-online.target
After=stabile-networking.service
After=network.target network-online.target
After=stabile-ubuntu.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-kubernetes.pl
TimeoutSec=500
RemainAfterExit=yes
Environment="HOME=/root"

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-kubernetes.service'
chmod 664 /etc/systemd/system/stabile-kubernetes.service

# Make mountpoint for local storage
mkdir /mnt/local