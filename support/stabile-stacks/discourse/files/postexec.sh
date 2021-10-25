#!/bin/bash

apt-add-repository -y ppa:brightbox/ruby-ng
apt-get update
apt-get -q -y --force-yes install ruby2.6 ruby2.6-dev

cp /var/discourse/config/discourse_defaults.conf /var/discourse/config/discourse.conf
perl -pi -e 's/db_host =.*/db_host = localhost/g' /var/discourse/config/discourse.conf
perl -pi -e 's/db_port =.*/db_port = 5432/g' /var/discourse/config/discourse.conf
perl -pi -e 's/db_password =.*/db_password = \"password\"/g' /var/discourse/config/discourse.conf
perl -pi -e 's/hostname =.*/hostname = discourse.stabile.io/g' /var/discourse/config/discourse.conf
perl -pi -e 's/smtp_address =.*/smtp_address = localhost/g' /var/discourse/config/discourse.conf
perl -pi -e 's/smtp_domain =.*/smtp_domain = stabile.io/g' /var/discourse/config/discourse.conf
perl -pi -e 's/smtp_authentication =.*/smtp_authentication = none/g' /var/discourse/config/discourse.conf
perl -pi -e 's/smtp_enable_start_tls =.*/smtp_enable_start_tls = false/g' /var/discourse/config/discourse.conf
perl -pi -e 's/APP_ROOT =.*/APP_ROOT = "\/var\/discourse\"/g' /var/discourse/config/puma.rb
perl -pi -e 's/bind .*/bind "tcp:\/\/0.0.0.0:9292"/g' /var/discourse/config/puma.rb
perl -pi -e 's/development test profile/development production test profile/g' /var/discourse/config/application.rb
perl -pi -e 's/(.*config.serve_static_files.+)/\#$1/g' /var/discourse/config/environments/production.rb

apt-get install -y npm
npm install -g svgo@0.7.2
#npm install pngquant
gem install image_optim
gem install image_optim_pack

perl -pi -e 's/inet_protocols =.*/inet_protocols = ipv4/;' /etc/postfix/main.cf

echo 'production:
  prepared_statements: false
  adapter: postgresql
  database: discourse
  min_messages: warning
  pool: 5
  timeout: 5000
  host_names: localhost' >> /var/discourse/config/database.yml

echo "---
:concurrency: 5
:pidfile: tmp/pids/sidekiq.pid
staging:
  :concurrency: 10
production:
  :concurrency: 20
  :queues:
    - [critical,4]
    - [default, 2]
    - [low]
development:
  :queues:
    - [critical,4]
    - [default, 2]
    - [low]" > /var/discourse/config/sidekiq.yml

mkdir -p /var/discourse/tmp/sockets
mkdir -p /var/discourse/tmp/pids

cd /var/discourse
#gem install bundler
# https://bundler.io/blog/2019/05/14/solutions-for-cant-find-gem-bundler-with-executable-bundle.html
gem install bundler -v "$(grep -A 1 "BUNDLED WITH" Gemfile.lock | tail -n 1)"
gem install uglifier
bundle install
echo "export RAILS_ENV=production" >> /etc/bash.bashrc

#lower password requirements
# https://github.com/discourse/discourse/commit/b2cfad5f47e6335ba514297517fa20e84dd004a8
wget https://github.com/mikefarah/yq/releases/download/v4.9.6/yq_linux_amd64
mv yq_linux_amd64 /usr/bin/yq
chmod 755 /usr/bin/yq
/usr/bin/yq e '.users.min_password_length.min = 6' -i /var/discourse/config/site_settings.yml
/usr/bin/yq e '.users.min_password_length.default = 6' -i /var/discourse/config/site_settings.yml
/usr/bin/yq e '.users.min_admin_password_length.min = 6' -i /var/discourse/config/site_settings.yml
/usr/bin/yq e '.users.min_admin_password_length.default = 6' -i /var/discourse/config/site_settings.yml
/usr/bin/yq e '.security.force_https.default = true' -i /var/discourse/config/site_settings.yml

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/

# Remove tabs from Webmin UI
rm -r /usr/share/webmin/stabile/tabs/commands
rm -r /usr/share/webmin/stabile/tabs/servers

cp /tmp/files/stabile-discourse.pl /usr/local/bin/

# Allow Discourse to be reaachable on alias URLs
mkdir /var/discourse/plugins/multiurl
cp /tmp/files/plugin.rb /var/discourse/plugins/multiurl

echo "<Directory /var/discourse/>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
</Directory>" >> /etc/apache2/apache2.conf

# Redirect to https
a2enmod rewrite
sed -i 's/DocumentRoot \/var\/www\/html/DocumentRoot \/var\/www\/html\nRewriteEngine On\nRewriteCond %{REQUEST_URI} !^\/.well-known\/\nRewriteRule (.*) https:\/\/%{HTTP_HOST}%{REQUEST_URI}/' /etc/apache2/sites-available/000-default.conf

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/discourse\/discourse_icon.png/' /usr/share/webmin/stabile/index.cgi
