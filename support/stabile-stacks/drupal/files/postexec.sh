#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Disable data image - this stack does not really need a data image
perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab

# Utility script for setting up drupal to work with this stack
cp /tmp/files/stabile-drupal.sh /usr/local/bin
chmod 755 $1/usr/local/bin/stabile-drupal.sh

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile Drupal
Wants=network-online.target
After=stabile-networking.service
After=mysql.service
After=network.target network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-drupal.sh
TimeoutSec=500
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-drupal.service'
chmod 664 /etc/systemd/system/stabile-drupal.service
systemctl enable stabile-drupal

# Configure Apache
mv /var/www/drupal-* /var/www/drupal;
echo "        Alias /drupal /var/www/drupal
        <Directory /var/www/drupal/>
            Options FollowSymlinks
            Require all granted
            RewriteEngine on
            #    RewriteBase /drupal
            RewriteCond %{REQUEST_FILENAME} !-f
            RewriteCond %{REQUEST_FILENAME} !-d
            RewriteCond %{REQUEST_URI} !=/favicon.ico
            RewriteRule ^(.*)$ /drupal/index.php?q=$1 [L,QSA]
        </Directory>" >> /etc/apache2/sites-available/default-ssl.conf

a2enmod rewrite
touch /var/www/drupal/.htaccess

# Make homepage redirect to blog
cp /var/www/html/index.html /var/www/html/index.html.bak
bash -c 'echo "<META HTTP-EQUIV=\"Refresh\" Content=\"0; URL=/drupal/\">" > /var/www/html/index.html'

# Install Drupal
# wget https://ftp.drupal.org/files/projects/drupal-8.9.20.tar.gz --directory-prefix /tmp
# tar -zxf /tmp/drupal-8.9.20.tar.gz
# mv /tmp/drupal-8.9.20 /var/www/drupal
# chown -R www-data:www-data /var/www/drupal
# chmod -R 755 /var/www/drupal

# Install drush
wget https://github.com/drush-ops/drush/releases/download/8.4.5/drush.phar --directory-prefix /tmp
cp /tmp/drush.phar /usr/local/bin/drush
chmod 755 /usr/local/bin/drush

# Create Drupal database directory
mkdir -p /var/lib/mysql/drupal_default
mkdir /var/lib/drupal
bash -c 'echo "default-character-set=utf8
default-collation=utf8_general_ci" > /var/lib/mysql/drupal_default/db.opt'
chown -R mysql:mysql /var/lib/mysql/drupal_default
systemctl enable mariadb.service

# Make a copy of default Drupal files for new sites
cp -a /var/www/drupal/sites/default/files /var/lib/drupal

# Bump up php limits
perl -pi -e 's/.*post_max_size = .*/post_max_size = 64M/;' /etc/php/7.4/apache2/php.ini
perl -pi -e 's/.*upload_max_filesize = .*/upload_max_filesize = 64M/;' /etc/php/7.4/apache2/php.ini
perl -pi -e 's/.*max_execution_time = .*/max_execution_time = 360/;' /etc/php/7.4/apache2/php.ini
perl -pi -e 's/.*memory_limit = .*/memory_limit = 256M/;' /etc/php/7.4/apache2/php.ini

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/

# Remove unneeded tabs
rm -r /usr/share/webmin/stabile/tabs/servers
rm -r /usr/share/webmin/stabile/tabs/commands

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/drupal\/logo-drupal.png/' /usr/share/webmin/stabile/index.cgi

# For debugging - allows ssh login from admin server. Remove before release.
#echo "stabile:stabile" | chpasswd
