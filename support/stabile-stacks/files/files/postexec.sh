#!/bin/bash

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
mv /tmp/files/stabile/elfinder /usr/share/webmin/stabile/
# Remove "command" tab from Webmin UI
rm -r /usr/share/webmin/stabile/tabs/commands
rm -r /usr/share/webmin/stabile/tabs/servers
#echo files > /etc/hostname
# Add 'files' to /etc/hosts
#perl -pi -e 's/(127.+localhost.*)/$1 files/;' /etc/hosts

# Install auth_tkt repo
echo "\n" | add-apt-repository "ppa:wiktel/ppa"
apt-get update
apt-get -q -y install libapache2-mod-auth-tkt
# apt-get -q -y install libpam-winbind libpam-krb5

# Redirect http to https
perl -pi -e 's/(DocumentRoot \/var\/www\/html)/$1\n\tRewriteEngine on\n\tRewriteCond \%{REQUEST_URI} !^\/public\/\n\tRewriteCond \%{REQUEST_URI} !^\/.well-known\/\n\tRewriteRule (.*) https:\/\/\%{HTTP_HOST}%{REQUEST_URI}/' /etc/apache2/sites-available/000-default.conf

bash -c 'echo "TKTAuthSecret \"AjyxgfFJ69234u\"
TKTAuthDigestType SHA512
SetEnv MOD_AUTH_TKT_CONF \"/etc/apache2/conf-available/auth_tkt.conf\"
Alias /auth /var/www/auth
<Location "/">
	RewriteEngine on
	RewriteCond "%{SERVER_PORT}" "^443$"
	RewriteCond %{REQUEST_URI} ^/\$
	RewriteRule (.*) /stabile/elfinder/index.cgi [R=301]
</Location>
<Directory /var/www/auth>
  Order deny,allow
  Allow from all
  Options -Indexes
  <FilesMatch \"\.cgi\$\">
    SetHandler perl-script
    PerlResponseHandler ModPerl::Registry
    PerlOptions +ParseHeaders
    Options +ExecCGI
  </FilesMatch>
  <FilesMatch \"\.pm\$\">
    Deny from all
  </FilesMatch>
</Directory>
<LocationMatch \"(/php/|/elfinder/index\.cgi)\">
    order deny,allow
    AuthName Services
    AuthType None
    TKTAuthLoginURL auth/login.cgi
    TKTAuthIgnoreIP on
    deny from all
    require valid-user
    Satisfy any
  <ifModule mod_headers.c>
     Header unset ETag
     Header set Cache-Control \"max-age=0, no-cache, no-store, must-revalidate\"
     Header set Pragma \"no-cache\"
     Header set Expires \"Wed, 11 Jan 1984 05:00:00 GMT\"
  </ifModule>
</LocationMatch>
<Location /stabile/elfinder/>
    ProxyPass http://127.0.0.1:10000/stabile/elfinder/
    ProxyPassReverse http://127.0.0.1:10000/stabile/elfinder/
</Location>
<Location /stabile/elfinder/elfinder/>
    ProxyPass http://127.0.0.1:10000/stabile/elfinder/
    ProxyPassReverse http://127.0.0.1:10000/stabile/elfinder/
</Location>
<LocationMatch \"(^/users/|^/shared/|^/groups/)\">
    order deny,allow
    Satisfy all
    AuthType None
    TKTAuthLoginURL auth/login.cgi
    TKTAuthIgnoreIP on
    require valid-user
    RewriteEngine On
    ## Prevent redirect loop
    RewriteCond %{ENV:REDIRECT_STATUS} ^\$
    RewriteRule users/[^\/]+(.*) /users/%{REMOTE_USER}\$1
    ## Require presence of file named \".groupaccess_user\" for each user in group who should have access
    SetEnvIf Request_URI \"^/groups/([^\/]+)/\" PATH_GROUP=\$1
    RewriteCond %{REQUEST_URI} ^\/groups\/
    RewriteCond \"/mnt/data/groups/%{ENV:PATH_GROUP}/.groupaccess_%{REMOTE_USER}\" !-f
    RewriteRule ^.*\$ - [E=NO_ACCESS:%{ENV:PATH_GROUP},G]
    Header set No_Access %{NO_ACCESS}e
</LocationMatch>
<LocationMatch \"auth_tkt=/\">
    TKTAuthTimeout 48h
</LocationMatch>
<Location \"/shared/\">
    AuthType None
    TKTAuthLoginURL auth/login.cgi
    TKTAuthIgnoreIP on
    require valid-user
# Disallow guest user 'g' access to shared - all other users have access
    RewriteEngine On
    RewriteCond %{REMOTE_USER} ^g$
    RewriteRule ^.*$ - [G]
</Location>
<Location \"/public/\">
   Options Indexes
   Require all granted
</Location>
" > /etc/apache2/conf-available/auth_tkt.conf'
ln -s /etc/apache2/conf-available/auth_tkt.conf /etc/apache2/conf-enabled/auth_tkt.conf

# Configure Samba
mv /etc/samba/smb.conf /etc/samba/smb.conf.orig
mv /etc/krb5.conf /etc/krb5.conf.orig
#samba-tool domain provision --realm=stabile.lan --domain=stabile --host-name=$dname --dnspass="Passw0rd" --adminpass="Passw0rd" --server-role=dc --dns-backend=SAMBA_INTERNAL --use-rfc2307 --use-xattrs=yes
samba-tool domain provision --realm=stabile.lan --domain=stabile --host-name=files --dnspass="Passw0rd" --adminpass="Passw0rd" --server-role=dc --dns-backend=SAMBA_INTERNAL --use-rfc2307
cp /var/lib/samba/private/krb5.conf /etc
# Prevent passwords from expiring
samba-tool domain passwordsettings set --max-pwd-age=0
# Disable systemd resolver
systemctl disable systemd-resolved
echo "nameserver 127.0.0.1
search stabile.lan" > /etc/resolv.conf
# Configure startup
systemctl mask smbd nmbd winbind
systemctl disable smbd nmbd winbind
systemctl unmask samba-ad-dc
systemctl enable samba-ad-dc

perl -pi -e 's/(\[global\])/$1\n   ldap server require strong auth =no\n   root preexec = \/bin\/mkdir \/mnt\/data\/users\/%U\n   log level = 2\n   log file = \/var\/log\/samba\/samba.log.%m\n   max log size = 50\n   debug timestamp = yes\n   idmap_ldb:use rfc2307 = yes\n   server services = -nbt\n   veto files = \/.groupaccess_*\/.tmb\/.quarantine\//' /etc/samba/smb.conf
perl -pi -e 's/(\[netlogon\])/$1\n   browseable = no/' /etc/samba/smb.conf
perl -pi -e 's/(\[sysvol\])/$1\n   browseable = no/' /etc/samba/smb.conf
bash -c 'echo "
[home]
   path = /mnt/data/users/%U
   read only = no
   browseable = yes
   hide dot files = yes
   hide unreadable = yes
   valid users = %U
   create mode = 0660
   directory mode = 0770
   inherit acls = Yes
   veto files = /aquota.user/lost+found/

[shared]
   path = /mnt/data/shared
   read only = no
   browseable = yes
   hide dot files = yes
   hide unreadable = yes
   create mode = 0660
   directory mode = 0770
   inherit acls = Yes

include = /etc/samba/smb.conf.groups

" >> /etc/samba/smb.conf'
touch /etc/samba/smb.conf.groups

# Make everything related to elfinder available through elfinder dir
ln -s /usr/share/webmin/stabile/bootstrap /usr/share/webmin/stabile/elfinder/bootstrap
ln -s /usr/share/webmin/stabile/strength /usr/share/webmin/stabile/elfinder/strength
ln -s /usr/share/webmin/stabile/css/flat-ui.css /usr/share/webmin/stabile/elfinder/css/flat-ui.css

# Finish configuring Apache
cp /tmp/files/ticketmaster.pl /usr/local/bin
chmod 755 /usr/local/bin/ticketmaster.pl
mkdir /etc/perl/Apache
cp /tmp/files/Apache/AuthTkt.pm $1/etc/perl/Apache

mkdir /var/www/auth
gunzip /usr/share/doc/libapache2-mod-auth-tkt/examples/cgi/login.cgi.gz
gunzip /usr/share/doc/libapache2-mod-auth-tkt/examples/cgi/Apache/AuthTkt.pm.gz
cp -a /usr/share/doc/libapache2-mod-auth-tkt/examples/cgi/* /var/www/auth
cp /tmp/files/auth-login.cgi /var/www/auth/login.cgi
chmod 755 $1/var/www/auth/*
cp /tmp/files/AuthTktConfig.pm /var/www/auth/

gcc -o /tmp/files/suid-smbpasswd /tmp/files/suid-smbpasswd.c
cp /tmp/files/suid-smbpasswd /usr/bin
chmod 6755 /usr/bin/suid-smbpasswd

ln -s /var/www/auth/login.cgi /var/www/auth/changepwd.cgi

/usr/sbin/a2enmod rewrite
/usr/sbin/a2enmod headers
/usr/sbin/a2enmod cgi


chmod 777 /mnt/data/shared /mnt/data/users /mnt/data/groups
ln -s /mnt/data/shared /var/www/html/shared
ln -s /mnt/data/users /var/www/html/users
ln -s /mnt/data/groups /var/www/html/groups

ln -sf /var/lib/samba/private/krb5.conf /etc/krb5.conf

/usr/sbin/adduser www-data users

# Set up btsync
bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for BTsync (Resilio Sync)
Wants=network-online.target
After=stabile-networking.service
After=network.target network-online.target

[Service]
ExecStart=/usr/share/webmin/stabile/tabs/samba/bittorrent_sync_x64/btsync --nodaemon --config /usr/share/webmin/stabile/tabs/samba/bittorrent_sync_x64/btconfig.json
TimeoutSec=60
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-btsync.service'
chmod 664 /etc/systemd/system/stabile-btsync.service
systemctl enable stabile-btsync

# Utility script for setting up Samba to work with this stack
cp /tmp/files/stabile-files.sh /usr/local/bin
chmod 755 /usr/local/bin/stabile-files.sh

bash -c 'echo "[Unit]
DefaultDependencies=no
Description=Utility script for Stabile Files
Wants=network-online.target
After=stabile-networking.service
After=network.target network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/stabile-files.sh
TimeoutSec=60
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-files.service'
chmod 664 /etc/systemd/system/stabile-files.service
systemctl enable stabile-files

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/files\/logo-files.png/' /usr/share/webmin/stabile/index.cgi
# Make elFinder display PDF's inline
# perl -pi -e "s/x-shockwave-flash'/pdf'/" /usr/share/webmin/stabile/elfinder/php/elFinder.class.php

# Make all files available to ElFinder when used through admin UI
ln -s /mnt/data /usr/share/webmin/stabile/files

# Bump up php limits
perl -pi -e 's/.*post_max_size = .*/post_max_size = 64M/;' /etc/php/7.2/cli/php.ini
perl -pi -e 's/.*upload_max_filesize = .*/upload_max_filesize = 64M/;' /etc/php/7.2/cli/php.ini

# For debugging - remove before release
#echo "stabile:stabile" | chpasswd
#echo "Passw0rd" | /usr/bin/kinit Administrator 2>&1

