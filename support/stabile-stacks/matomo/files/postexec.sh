#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
# Remove "command" tab from Webmin UI
rm -r /usr/share/webmin/stabile/tabs/commands
rm -r /usr/share/webmin/stabile/tabs/servers
echo matomo > /etc/hostname
cp /usr/share/webmin/stabile/tabs/matomo/stabile-matomo.pl /usr/local/bin/
ln -s /usr/local/bin/stabile-matomo.pl /etc/cron.hourly

echo "[Unit]
DefaultDependencies=no
Description=stabile matomo
After=network-online.target stabile-ubuntu.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/stabile-matomo.pl
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-matomo.service
systemctl enable stabile-matomo.service

# Configure Apache
chown -R www-data:www-data /var/www/matomo
# rm -Rf /var/www/html/matomo/plugins/Morpheus/icons/submodules
cp /usr/share/webmin/stabile/tabs/matomo/config.ini.php /var/www/matomo/config/config.ini.php
chown www-data:www-data /var/www/matomo/config/config.ini.php

echo "        Alias /matomo /var/www/matomo
" >> /etc/apache2/sites-available/default-ssl.conf

echo "<Directory /var/www/matomo/config>
    Require all denied
</Directory>
<Directory /var/www/matomo/tmp>
    Require all denied
</Directory>
<Directory /var/www/matomo/lang>
    Require all denied
</Directory>" >> /etc/apache2/apache2.conf

# Configure GeoIP
echo "AccountID 488358
LicenseKey 8X2C0cQVAaac0Cam" >> /etc/GeoIP.conf
echo y | composer require geoip2/geoip2
geoipupdate -v
ln -s /var/lib/GeoIP/GeoLite2-City.mmdb /var/www/matomo/misc/

# Configure dbip
gunzip /tmp/files/dbip-city-lite-2022-10.mmdb.gz
mv /tmp/files/dbip-city-lite-2022-10.mmdb /var/www/matomo/misc/DBIP-City.mmdb

# Tune MariaDB
perl -pi -e 's/#max_allowed_packet .*/max_allowed_packet = 128M/' /etc/mysql/mariadb.conf.d/50-server.cnf

# Make homepage redirect to blog
cp /var/www/html/index.html /var/www/html/index.html.bak
bash -c 'echo "<META HTTP-EQUIV=\"Refresh\" Content=\"0; URL=/matomo/\">" > /var/www/html/index.html'

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/matomo\/logo-matomo.png/' /usr/share/webmin/stabile/index.cgi
