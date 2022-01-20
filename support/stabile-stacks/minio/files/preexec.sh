#!/bin/bash

# This script is executed in the image chroot
echo "Performing pre-install operations"

# Disable data image - this stack does not really need a data image
# perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab

# Utility script for setting up minio to work with this stack
cp /tmp/files/stabile-minio.pl /usr/local/bin
chmod 755 /usr/local/bin/stabile-minio.pl

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile minio
Wants=network-online.target
After=stabile-networking.service remote-fs.target nss-lookup.target apache2.service

[Service]
Type=simple
ExecStart=/usr/local/bin/stabile-minio.pl
TimeoutSec=120
WorkingDirectory=/home/stabile
User=1001
Restart=always

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-minio.service'
chmod 664 /etc/systemd/system/stabile-minio.service
systemctl enable stabile-minio.service

# Systemd unit for Prometheus
bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for starting Prometheus
Wants=network-online.target
After=stabile-networking.service remote-fs.target nss-lookup.target apache2.service

[Service]
Type=simple
ExecStart=/usr/local/bin/prometheus --config.file=/etc/prometheus.yml --web.listen-address="127.0.0.1:9090"
TimeoutSec=120
WorkingDirectory=/home/stabile
User=1001
Restart=always

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-prometheus.service'
chmod 664 /etc/systemd/system/stabile-prometheus.service
systemctl enable stabile-prometheus.service

echo "stabile ALL=(ALL) NOPASSWD: ALL" /etc/sudoers.d/stabile

# For debugging - remove before release
# echo "stabile:stabile" | chpasswd
