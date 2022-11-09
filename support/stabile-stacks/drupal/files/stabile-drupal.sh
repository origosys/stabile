#!/bin/bash

if grep --quiet "User password:" /root/drupal_install.out; then
	echo "Modifications already made"
else
	echo "Installing Drupal default site"
  echo "CREATE USER 'drupal'@'localhost';" | mysql
  echo "GRANT ALL PRIVILEGES ON *.* TO 'drupal'@'localhost';" | mysql
  echo "FLUSH PRIVILEGES;" | mysql
  cd /var/www/drupal
  drush -y site-install standard --db-url='mysql://drupal@localhost/drupal_default' --site-name=Drupal > /root/drupal_install.out 2>&1
  chown -R www-data:www-data /var/www/drupal/sites/default
  chmod -R u+w /var/www/drupal/sites/default
fi
