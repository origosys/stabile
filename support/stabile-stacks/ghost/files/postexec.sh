#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
# Remove "command" tab from Webmin UI
rm -r /usr/share/webmin/stabile/tabs/commands
rm -r /usr/share/webmin/stabile/tabs/servers
echo ghost > /etc/hostname

# Install Ghost according to: https://ghost.org/docs/install/ubuntu/
#useradd ghostuser
#usermod -L ghostuser
#usermod -aG sudo ghostuser

groupadd --gid 999 ghost
useradd -M --uid 999 --gid 999 ghost
usermod -L ghost
usermod -aG sudo ghost
chsh -s /bin/bash ghost

curl -sL https://deb.nodesource.com/setup_14.x | sudo -E bash
apt-get install -y nodejs
npm install ghost-cli@latest -g
apt-get install -y mysql-server

mkdir /var/www/ghost
chmod 777 /var/www/ghost
sudo -H -u stabile ghost install --auto --dir /var/www/ghost --auto --no-setup --no-prompt --no-start --no-stack --db=sqlite3

echo '{
  "url": "https://ghosturl",
  "server": {
    "port": 2368,
    "host": "127.0.0.1"
  },
  "database": {
    "client": "mysql",
    "connection": {
      "host": "localhost",
      "user": "ghost",
      "password": "sunshine",
      "database": "ghost"
    }
  },
  "mail": {
    "transport": "Direct"
  },
  "logging": {
    "transports": [
      "file",
      "stdout"
    ]
  },
  "process": "systemd",
  "paths": {
    "contentPath": "/var/www/ghost/content"
  }
}' > /var/www/ghost/config.production.json
chown -R ghost:ghost /var/www/ghost
#sudo -H -u ghostuser ghost setup --auto --dir /var/www/ghost systemd

# Configure Apache
a2enmod proxy_wstunnel
a2enmod rewrite
a2enmod lbmethod_byrequests
a2enmod proxy_balancer
a2enmod headers

sed -i 's/DocumentRoot \/var\/www\/html/DocumentRoot \/var\/www\/html\nProxyRequests Off\nRequestHeader set X-Forwarded-Proto "https"\nProxyPreserveHost On\n<Location \/>\nProxyPass http:\/\/127.0.0.1:2368\/\nProxyPassReverse http:\/\/127.0.0.1:2368\/\n<\/Location>\n/' /etc/apache2/sites-available/default-ssl.conf

sed -i 's/DocumentRoot \/var\/www\/html/DocumentRoot \/var\/www\/html\nRewriteEngine On\nRewriteCond %{REQUEST_URI} !^\/.well-known\/\nRewriteRule (.*) https:\/\/%{HTTP_HOST}%{REQUEST_URI}/' /etc/apache2/sites-available/000-default.conf

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/ghost\/ghost-logo.png/' /usr/share/webmin/stabile/index.cgi



