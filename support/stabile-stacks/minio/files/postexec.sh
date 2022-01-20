#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
# Remove "command" tab from Webmin UI
rm -r /usr/share/webmin/stabile/tabs/commands
rm -r /usr/share/webmin/stabile/tabs/servers
echo minio > /etc/hostname

# Install Minio according to: https://docs.min.io/minio/baremetal/
cd /usr/local/bin
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc

chmod -R 777 /mnt/data

# Install Prometheus according to https://prometheus.io/docs/prometheus/latest/getting_started/#downloading-and-running-prometheus
cd /opt
wget https://github.com/prometheus/prometheus/releases/download/v2.31.1/prometheus-2.31.1.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-2.31.1.linux-amd64
ln -s /opt/prometheus-2.31.1.linux-amd64/prometheus /usr/local/bin/prometheus
ln -s /opt/prometheus-2.31.1.linux-amd64/promtool /usr/local/bin/promtool

echo "global:
   scrape_interval: 15s

scrape_configs:
   - job_name: minio-job
     metrics_path: /minio/v2/metrics/cluster
     scheme: http
     static_configs:
     - targets: [localhost:9000]
" > /etc/prometheus.yml


# Configure Apache
a2enmod proxy_wstunnel
a2enmod rewrite
a2enmod lbmethod_byrequests
a2enmod proxy_balancer
a2enmod headers

echo "ProxyRequests Off
ProxyVia Block
ProxyPreserveHost On

<Proxy *>
     Require all granted
</Proxy>

RewriteEngine On
RewriteCond %{HTTP:Upgrade} =websocket [NC]
RewriteRule /(.*)           ws://127.0.0.1:9001/\$1 [P,L]
RewriteCond %{HTTP:Upgrade} !=websocket [NC]
RewriteRule /(.*)           http://127.0.0.1:9001/\$1 [P,L]

<Location />
ProxyPass http://127.0.0.1:9001/
ProxyPassReverse http://127.0.0.1:9001/
Require ip 127.0.0.1
</Location>
" > /etc/apache2/conf-available/minio.conf


sed -i 's/DocumentRoot \/var\/www\/html/DocumentRoot \/var\/www\/html\n		Include \/etc\/apache2\/conf-available\/minio.conf\n/' /etc/apache2/sites-available/default-ssl.conf

sed -i 's/DocumentRoot \/var\/www\/html/DocumentRoot \/var\/www\/html\nRewriteEngine On\nRewriteCond %{REQUEST_URI} !^\/.well-known\/\nRewriteRule (.*) https:\/\/%{HTTP_HOST}%{REQUEST_URI}/' /etc/apache2/sites-available/000-default.conf

chown 1001 /etc/apache2/conf-available/minio.conf
chmod 777 /etc/apache2/conf-available

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/minio\/minio-emblem.png/' /usr/share/webmin/stabile/index.cgi



