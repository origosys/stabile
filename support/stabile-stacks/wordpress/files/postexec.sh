#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Disable data image - this stack does not really need a data image
perl -pi -e 's/(\/dev\/vdb1.+)/#$1/;' /etc/fstab

# Utility script for setting up WordPress to work with this stack
cp /tmp/files/stabile-wordpress.sh /usr/local/bin
chmod 755 $1/usr/local/bin/stabile-wordpress.sh

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile WordPress
Wants=network-online.target
After=stabile-networking.service
After=mysql.service
After=network.target network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-wordpress.sh
TimeoutSec=60
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-wordpress.service'
chmod 664 /etc/systemd/system/stabile-wordpress.service

# Configure Apache

bash -c 'echo "Alias /home /usr/share/wordpress
Alias /home/wp-content /var/lib/wordpress/wp-content
<Directory /usr/share/wordpress>
Options FollowSymLinks
AllowOverride Limit Options FileInfo
DirectoryIndex index.php
Order allow,deny
Allow from all
</Directory>
<Directory /var/lib/wordpress/wp-content>
Options FollowSymLinks
Order allow,deny
Allow from all
</Directory>" >> /etc/apache2/sites-available/default-ssl.conf'

# Configure WordPress

echo  "<?php
define('DB_NAME', 'wordpress_default');
define('DB_USER', 'root');
define('DB_PASSWORD', '');
define('DB_HOST', 'localhost');
define('WP_CONTENT_DIR', '/usr/share/wordpress/wp-content');
define('WP_HOME','/home');
define('WP_SITEURL','/home');
define('WP_CACHE', true);
define('WP_ CORE_UPDATE', true);
?>" >> /etc/wordpress/config-default.php

# Fix link to install.css
perl -pi -e 's/(<\?php wp_admin_css\(.+install.+ true \); \?>)/<link rel="stylesheet" id="install-css"  href="css\/install\.css" type="text\/css" media="all" \/>/;' /usr/share/wordpress/wp-admin/install.php

# Make install page prettier in stabile configure dialog
perl -pi -e 's/margin:2em auto/margin:0 auto/;' /usr/share/wordpress/wp-admin/css/install.css

# Redirect to Webmin when WordPress is installed
perl -pi -e 's/(<table class="form-table install-success">)/$1\n<script>var tab="<?php echo \$_SERVER[HTTP_HOST]; ?>"; if ( tab.indexOf(".")!==-1 ) tab=tab.substring(0,tab.indexOf(".")); if (tab === "127") tab="default"; tab=tab+"-site"; var pipeloc=location.href.substring(0,location.href.indexOf("\/home")); location=pipeloc + ":10000\/stabile\/?tab=" + tab;<\/script>/;' /usr/share/wordpress/wp-admin/install.php

perl -pi -e 's/(action="install.php\?step=2)/$1&host=<?php echo \$_SERVER[HTTP_HOST]; ?>/;' /usr/share/wordpress/wp-admin/install.php
perl -pi -e 's/(.* action="\?step=1".*)/            echo "<form id=setup method=post action=?step=1&host=\$_SERVER[HTTP_HOST]>";/;' /usr/share/wordpress/wp-admin/install.php

# Ask stabile to change the managementlink from Wordpress install page, so the above redirect is not needed on subsequent loads
perl -pi -e 's/(if \( is_blog_installed\(\) \) \{)/$1\n    \`curl -k -X PUT --data-urlencode "PUTDATA={\\"uuid\\":\\"this\\",\\"managementlink\\":\\"\/stabile\/pipe\/http:\/\/{uuid}:10000\/wordpress\/\\"}" https:\/\/10.0.0.1\/stabile\/images\`;/;' /usr/share/wordpress/wp-admin/install.php

# Make homepage redirect to blog
cp /var/www/html/index.html /var/www/html/index.html.bak
bash -c 'echo "<META HTTP-EQUIV=\"Refresh\" Content=\"0; URL=/home/\">" > /var/www/html/index.html'

# Create WordPress database
mkdir -p /var/lib/mysql/wordpress_default
bash -c 'echo "default-character-set=utf8
default-collation=utf8_general_ci" > /var/lib/mysql/wordpress_default/db.opt'

chown -R mysql:mysql /var/lib/mysql/wordpress_default

systemctl enable mysql

# Allow theme installation automatic upgrades etc
chown -R www-data:www-data /var/lib/wordpress
chown -R www-data:www-data /usr/share/wordpress
chown -R www-data:www-data /usr/share/javascript/cropper/
chown -R www-data:www-data /usr/share/javascript/prototype/
chown -R www-data:www-data /usr/share/php
chown -R www-data:www-data /usr/share/tinymce

# Install php 7.4
# Install auth_tkt repo
echo "\n" | add-apt-repository "ppa:ondrej/php"
apt-get update
apt-get -q -y install php7.4 php7.4-cli php7.4-common php7.4-curl php7.4-intl php7.4-json php7.4-mysql php7.4-opcache php7.4-readline php7.4-xml
a2enmod php7.4
a2dismod php7.2

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/

# Remove unneeded tabs
rm -r /usr/share/webmin/stabile/tabs/servers
rm -r /usr/share/webmin/stabile/tabs/commands

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/wordpress\/logo-wordpress.png/' /usr/share/webmin/stabile/index.cgi

# For debugging - allows ssh login from admin server. Remove before release.
#echo "stabile:stabile" | chpasswd
