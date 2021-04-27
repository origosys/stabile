#!/bin/bash

# The version of the app we are building
version="1.4"
#dname=`basename "$PWD"`
dname="origo-samba"
me=`basename $0`

# Change working directory to script's directory
cd ${0%/*}
# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
# Remove "command" tab from Webmin UI
rm -r /usr/share/webmin/stabile/tabs/commands
echo files > /etc/hostname

# Add Samba4 repo
add-apt-repository "deb http://ppa.launchpad.net/kernevil/samba-4.0/ubuntu precise main"
apt-get update
apt-get -q -y --force-yes install samba4

# Install auth_tkt repo
add-apt-repository "ppa:wiktel/ppa"
apt-get update
apt-get -q -y --force-yes install libapache2-mod-auth-tkt-prefork

bash -c 'echo "TKTAuthSecret \"AjyxgfFJ69234u\"
TKTAuthDigestType SHA512
SetEnv MOD_AUTH_TKT_CONF \"/etc/apache2/conf.d/auth_tkt.conf\"
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
    TKTAuthLoginURL /auth/login.cgi
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
<Location /origo/elfinder/>
    ProxyPass http://127.0.0.1:10000/origo/elfinder/
    ProxyPassReverse http://127.0.0.1:10000/origo/elfinder/
</Location>
<LocationMatch \"(^/users/|^/shared/|^/groups/)\">
    order deny,allow
    Satisfy all
    AuthType None
    TKTAuthLoginURL /auth/login.cgi
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
</Location>
" > /etc/apache2/conf.d/auth_tkt.conf'

# Configure Samba
samba-tool domain provision --realm=origo.lan --domain=origo --host-name=$dname --dnspass="Passw0rd" --adminpass="Passw0rd" --server-role=dc --dns-backend=SAMBA_INTERNAL --use-rfc2307 --use-xattrs=yes
# Prevent passwords from expiring
samba-tool domain passwordsettings set --max-pwd-age=0

perl -pi -e 's/(\[global\])/$1\n   root preexec = \/bin\/mkdir \/mnt\/data\/users\/%U\n   dns forwarder = 10.0.0.1\n   log level = 2\n   log file = \/var\/log\/samba\/samba.log.%m\n   max log size = 50\n   debug timestamp = yes\n   idmap_ldb:use rfc2307 = yes\n   server services = -nbt\n   veto files = \/.groupaccess_*\/.tmb\/.quarantine\//' /etc/samba/smb.conf
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
touch $1/etc/samba/smb.conf.groups

# Make everything related to elfinder available through elfinder dir
ln -s /usr/share/webmin/origo/bootstrap /usr/share/webmin/origo/elfinder/bootstrap
ln -s /usr/share/webmin/origo/strength /usr/share/webmin/origo/elfinder/strength
ln -s /usr/share/webmin/origo/css/flat-ui.css /usr/share/webmin/origo/elfinder/css/flat-ui.css
ln -s /usr/share/webmin/origo/images/origo-gray.png /usr/share/webmin/origo/elfinder/img/origo-gray.png

# Finish configuring Apache
cp ticketmaster.pl $1/usr/local/bin
chmod 755 $1/usr/local/bin/ticketmaster.pl
mkdir $1/etc/perl/Apache
cp Apache/AuthTkt.pm $1/etc/perl/Apache

mkdir $1/var/www/auth
gunzip $1/usr/share/doc/libapache2-mod-auth-tkt-prefork/cgi/login.cgi.gz
gunzip $1/usr/share/doc/libapache2-mod-auth-tkt-prefork/cgi/Apache/AuthTkt.pm.gz
cp -a $1/usr/share/doc/libapache2-mod-auth-tkt-prefork/cgi/* $1/var/www/auth
cp auth-login.cgi $1/var/www/auth/login.cgi
chmod 755 $1/var/www/auth/*
cp AuthTktConfig.pm $1/var/www/auth/

gcc -o suid-smbpasswd suid-smbpasswd.c
cp suid-smbpasswd $1/usr/bin
chmod 6755 $1/usr/bin/suid-smbpasswd

ln -s /var/www/auth/login.cgi /var/www/auth/changepwd.cgi

/usr/sbin/a2enmod rewrite
/usr/sbin/a2enmod headers

#    mkdir /mnt/data/users
#    mkdir /mnt/data/users/administrator
#    mkdir /mnt/data/shared
#    mkdir /mnt/data/groups
rm -r /usr/share/webmin/origo/files

ln -s /mnt/data/shared /var/www/shared
ln -s /mnt/data/users /var/www/users
ln -s /mnt/data/groups /var/www/groups

ln -sf /opt/samba4/private/krb5.conf /etc/krb5.conf

/usr/sbin/adduser www-data users

# Set up btsync
bash -c 'echo "start on started networking
expect fork
respawn
exec /usr/share/webmin/origo/tabs/samba/bittorrent_sync_x64/btsync --nodaemon --config /usr/share/webmin/origo/tabs/samba/bittorrent_sync_x64/btconfig.json &" > /etc/init/origo-btsync.conf'

# Utility script for setting up Samba to work with this stack
cp /tmp/files/stabile-files.sh /usr/local/bin
chmod 755 $1/usr/local/bin/stabile-files.sh

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

