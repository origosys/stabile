#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Install Codiad

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/mongodb\/logo-mongodb.png/' /usr/share/webmin/stabile/index.cgi

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
# Remove tabs from Webmin UI
# rm -r /usr/share/webmin/stabile/tabs/servers

echo "*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -s 127.0.0.1 -p tcp -m tcp --dport 27017 -j ACCEPT
-A INPUT ! -s 10.0.0.0/8 -p tcp -m tcp --dport 27017 -j DROP
COMMIT" > /etc/iptables/rules.v4

systemctl enable mongod
perl -pi -e 's/  bindIp: .*/  bindIp: 0.0.0.0/;' /etc/mongod.conf
systemctl enable stabile-mongodb

touch /etc/apache2/mongodbpasswords
a2enmod rewrite
cp /tmp/files/default-ssl.conf /etc/apache2/sites-available
php -r "copy('https://getcomposer.org/installer', '/tmp/composer-setup.php');"
php /tmp/composer-setup.php
mv composer.phar /usr/local/bin/composer
cd /var/www/mongodb-php-gui ; echo 'y' | composer require mongodb/mongodb
cd /var/www/mongodb-php-gui ; echo 'y' | composer install
