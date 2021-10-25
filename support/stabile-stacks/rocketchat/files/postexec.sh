#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
# Remove "command" tab from Webmin UI
rm -r /usr/share/webmin/stabile/tabs/commands
rm -r /usr/share/webmin/stabile/tabs/servers
echo rocketchat > /etc/hostname

# Install Rocket.Chat according to: https://docs.rocket.chat/installing-and-updating/manual-installation/ubuntu

# First install dependencies
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4
echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-4.0.list
# Not needed:
# apt-get -y update && apt-get install -y curl && curl -sL https://deb.nodesource.com/setup_12.x | bash -
apt-get -y update
apt-get install -y build-essential mongodb-org nodejs graphicsmagick
apt-get install -y npm
npm install -g inherits n && n 12.18.4

# Install bcrypt cli
# npm install --global bcrypt-cli

# Then Rocket.Chat
curl -L https://releases.rocket.chat/latest/download -o /tmp/rocket.chat.tgz
tar -xzf /tmp/rocket.chat.tgz -C /tmp
cd /tmp/bundle/programs/server && npm install
mv /tmp/bundle /opt/Rocket.Chat

# Configure Rocket.Chat
useradd -M rocketchat && usermod -L rocketchat
chown -R rocketchat:rocketchat /opt/Rocket.Chat
cat << EOF |tee -a /lib/systemd/system/rocketchat.service
[Unit]
Description=The Rocket.Chat server
After=network.target remote-fs.target nss-lookup.target apache2.service mongod.service
[Service]
ExecStart=/usr/local/bin/node /opt/Rocket.Chat/main.js
Environment=OVERWRITE_SETTING_Show_Setup_Wizard=completed SETTINGS_REQUIRED_ON_WIZARD=
Environment=ADMIN_EMAIL=
Environment=ADMIN_USERNAME=stabile
Environment=ADMIN_PASS=
Environment=MONGO_URL=mongodb://localhost:27017/rocketchat?replicaSet=rs01 MONGO_OPLOG_URL=mongodb://localhost:27017/local?replicaSet=rs01 ROOT_URL=http://localhost:3000/ PORT=3000
StandardOutput=syslog
StandardError=syslog
Restart=on-failure
SyslogIdentifier=rocketchat
User=rocketchat
TimeoutSec=240
[Install]
WantedBy=multi-user.target
EOF

sed -i "s/^#  engine:/  engine: mmapv1/"  /etc/mongod.conf
sed -i "s/^#replication:/replication:\n  replSetName: rs01/" /etc/mongod.conf
systemctl enable mongod

# Bump up timeout because of the high CPU-load of this stack
sed -i "s/TimeoutSec=60/TimeoutSec=240/"  /etc/systemd/system/stabile-ubuntu.service
sed -i 's/TasksAccounting=false/TasksAccounting=false\nTimeoutSec=240/'  /lib/systemd/system/mongod.service

# Make units waiting for mongod not fire before mongod is actually ready
sed -i 's/PIDFile=\/var\/run\/mongodb\/mongod.pid/#PIDFile=\/var\/run\/mongodb\/mongod.pid\nExecStartPost=\/bin\/sh -c "while ! \/usr\/bin\/mongo --eval \\"db.version()\\" > \/dev\/null 2>\&1; do sleep 0.5; done"/' /lib/systemd/system/mongod.service

# Moved to stabile-rocketchat.pl
# mongo --eval "printjson(rs.initiate())"
systemctl enable rocketchat

# Configure Apache
a2enmod proxy_wstunnel
a2enmod rewrite

a2enmod lbmethod_byrequests
a2enmod proxy_balancer

sed -i 's/DocumentRoot \/var\/www\/html/DocumentRoot \/var\/www\/html\n<Location \/>\nRequire all granted\n<\/Location>\n<Proxy balancer:\/\/rocketclusterws>\nBalancerMember ws:\/\/localhost:3000\n<\/Proxy>\n<Proxy balancer:\/\/rocketcluster>\nBalancerMember http:\/\/localhost:3000\n<\/Proxy>\nRewriteEngine On\nRewriteCond %{HTTP:CONNECTION} Upgrade [NC]\nRewriteCond %{HTTP:Upgrade} =websocket [NC]\nRewriteRule \/(.*)           balancer:\/\/rocketclusterws\/\$1 [P,L]\nRewriteCond %{HTTP:Upgrade} !=websocket [NC]\nRewriteRule \/(.*)           balancer:\/\/rocketcluster\/\$1 [P,L]\nProxyPassReverse \/          balancer:\/\/rocketcluster\/\n/' /etc/apache2/sites-available/default-ssl.conf

sed -i 's/DocumentRoot \/var\/www\/html/DocumentRoot \/var\/www\/html\nRewriteEngine On\nRewriteCond %{REQUEST_URI} !^\/.well-known\/\nRewriteRule (.*) https:\/\/%{HTTP_HOST}%{REQUEST_URI}/' /etc/apache2/sites-available/000-default.conf

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/rocketchat\/rocketchat-logo.svg/' /usr/share/webmin/stabile/index.cgi



