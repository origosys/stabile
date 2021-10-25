#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
# Remove "command" tab from Webmin UI
rm -r /usr/share/webmin/stabile/tabs/commands
rm -r /usr/share/webmin/stabile/tabs/servers
echo zimbra > /etc/hostname
# hostname zimbra

perl -pi -e 's/.* ubuntu-bionic//' /etc/hosts
echo 127.0.0.1 zimbra.stabile.int zimbra >> /etc/hosts

# link='https://raw.githubusercontent.com/meramsey/zimbra-automated-installation/master/ZimbraEasyInstall.sh'; bash <(curl -s ${link} || wget -qO - ${link}) stabile.io --ip 127.0.0.1 --password Origo42

## Preparing all the variables like IP, Hostname, etc, all of them from the container
RANDOMHAM=$(date +%s|sha256sum|base64|head -c 10)
RANDOMSPAM=$(date +%s|sha256sum|base64|head -c 10)
RANDOMVIRUS=$(date +%s|sha256sum|base64|head -c 10)
HOSTNAME="zimbra.stabile.int"

# Bash ternary's for below are done via parameter expansion used to define main variables with defaults: https://stackoverflow.com/a/12691027/1621381
# Timezone if not provided is determined automagically...
TIMEZONE="$(date +%Z)"
# IP if not provided is determined automagically...
IP="127.0.0.1"
DOMAIN="stabile.int"
# Password if not provided is determined automagically...
PASSWORD="${_arg_password:-$(openssl rand -base64 12)}"

# keystrokes with fallback
keystrokes='/tmp/files/stabile/installZimbra-keystrokes'
# zimbrascript with fallback
zimbrascript='/tmp/files/stabile/installZimbraScript'
zimbrafolder='zcs-8.8.15_GA_3869.UBUNTU18_64.20190918004220'

DEBIAN_FRONTEND=noninteractive apt install -y locales
locale-gen "en_US.UTF-8"
update-locale LC_ALL="en_US.UTF-8"

# PERL_MM_USE_DEFAULT=1 perl -MCPAN -e 'install URI::Escape'

systemctl disable systemd-resolved.service;
sed -i 's|#DNSStubListener=yes|DNSStubListener=no|g' /etc/systemd/resolved.conf;
rm /etc/resolv.conf;
echo 'nameserver 1.1.1.1
nameserver 8.8.8.8' >> /etc/resolv.conf

echo "Installing dnsmasq DNS Server"
DEBIAN_FRONTEND=noninteractive apt-get install -y dnsmasq
echo "Configuring DNS Server"
 mv /etc/dnsmasq.conf /etc/dnsmasq.conf.original
# Reference for indented heredocs: https://unix.stackexchange.com/a/11426/440352
cat >> /etc/dnsmasq.conf <<-EOL
server=8.8.8.8
listen-address=127.0.0.1
domain=${DOMAIN}
mx-host=${DOMAIN},$HOSTNAME.${DOMAIN},0
address=/$HOSTNAME.${DOMAIN}/${IP}
EOL
systemctl enable dnsmasq

# Fix placeholders
sed -i -e "s|RANDOMHAM_PLACEHOLDER|${RANDOMHAM}|g" ${zimbrascript}
sed -i -e "s|RANDOMSPAM_PLACEHOLDER|${RANDOMSPAM}|g" ${zimbrascript}
sed -i -e "s|RANDOMVIRUS_PLACEHOLDER|${RANDOMVIRUS}|g" ${zimbrascript}
sed -i -e "s|HOSTNAME_PLACEHOLDER|${HOSTNAME}|g" ${zimbrascript}
sed -i -e "s|TIMEZONE_PLACEHOLDER|${TIMEZONE}|g" ${zimbrascript}
sed -i -e "s|IP_PLACEHOLDER|${IP}|g" ${zimbrascript}
sed -i -e "s|DOMAIN_PLACEHOLDER|${DOMAIN}|g" ${zimbrascript}
sed -i -e "s|PASSWORD_PLACEHOLDER|${PASSWORD}|g" ${zimbrascript}

echo "Installing Zimbra Collaboration Software Only"
# echo "10.2.0.19 files.origo.io" >> /etc/hosts;
cd "/tmp/files/stabile"/ && wget "https://files.origo.io/pub/${zimbrafolder}.tgz"
cd "/tmp/files/stabile"/ && tar -zxf ${zimbrafolder}.tgz
cd "/tmp/files/stabile/${zimbrafolder}"/ && ./install.sh -s < "${keystrokes}"
echo "Installing Zimbra Collaboration and injecting the configuration"
/opt/zimbra/libexec/zmsetup.pl -c "${zimbrascript}"

# https://origo.io/info/running-your-own-emission-free-email-server/
sed -i -e "s|# COMMONLY ADJUSTED SETTINGS:|# COMMONLY ADJUSTED SETTINGS:\n\$warnspamsender = 0;\n\$warnbadhsender = 0;\n\$warnvirussender = 0;\n\$warnbannedsender = 0;|g" /opt/zimbra/conf/amavisd.conf.in

# Configure Apache
sed -i 's/DocumentRoot \/var\/www\/html/DocumentRoot \/var\/www\/html\nRewriteEngine On\nRewriteCond %{REQUEST_URI} !^\/.well-known\/\nRewriteCond %{REQUEST_URI} !^\/dns\/\nRewriteCond %{REQUEST_URI} !^\/icons\/\nRewriteRule (.*) https:\/\/%{HTTP_HOST}%{REQUEST_URI}/' /etc/apache2/sites-available/000-default.conf
# Disable Apache SSL - Zimbra has its own web server
sed -i 's/Listen 443/# Listen 443/' /etc/apache2/ports.conf
a2enmod rewrite
a2dissite default-ssl

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/zimbra\/zimbra-no-lettermark.png/' /usr/share/webmin/stabile/index.cgi

#pkill -f zimbra
killall rsyslogd
killall slapd
killall mysqld_safe
killall mysqld
