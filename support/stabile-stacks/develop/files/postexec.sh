#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Install Codiad
rm -r /var/www/html
mv /var/www/codiad /var/www/html
mv /tmp/files/config.php /var/www/html/
chown www-data:www-data /var/www
echo '<?php/*|[{"username":"stabile","password":"","project":"My Project"}]|*/?>' > /var/www/html/data/users.php
echo '<?php/*|[{"name":"My Project","path":"MyProject"}]|*/?>' > /var/www/html/data/projects.php
echo '<?php/*|[""]|*/?>' > /var/www/html/data/active.php
echo '<?php/*|{"c":"c_cpp","coffee":"coffee","cpp":"c_cpp","css":"css","d":"d","erb":"html_ruby","h":"c_cpp","hpp":"c_cpp","htm":"html","html":"html","jade":"jade","java":"java","js":"javascript","json":"json","less":"less","md":"markdown","php":"php","php4":"php","php5":"php","phtml":"php","py":"python","rb":"ruby","sass":"scss","scss":"scss","sql":"sql","tpl":"html","vm":"velocity","xml":"xml","pl":"perl","cgi":"perl"}|*/?>' > /var/www/html/data/extensions.php

# Make a simple project with a Python file
mkdir "/var/www/html/workspace/MyProject"
echo "#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# enable debugging
import cgitb
cgitb.enable()

print 'Content-Type: text/html;charset=utf-8'
print
print '<h1>Hello World!</h1>'" > /var/www/html/workspace/MyProject/hello.py
chmod 755 /var/www/html/workspace/MyProject/hello.py

# Install some Codiad plugins
cd /var/www/html/plugins
git clone https://github.com/Andr3as/Codiad-Permissions
git clone https://github.com/daeks/Codiad-Together
# git clone https://github.com/Andr3as/Codiad-Beautify
# git clone https://github.com/Andr3as/Codiad-CodeTransfer
git clone https://github.com/Andr3as/Codiad-CodeGit
git clone https://github.com/Fluidbyte/Codiad-Terminal
perl -pi -e 's/terminal//' /var/www/html/plugins/Codiad-Terminal/emulator/term.php
chown www-data:www-data -R /var/www/html/
a2enmod cgi
a2enmod actions
echo 'AddHandler cgi-script cgi pl py
AddHandler cgi-node .jss
Action cgi-node /cgi-bin/cgi-node.js
<Directory "/var/www/html">
   Options ExecCGI
</Directory>' >> /etc/apache2/conf-available/serve-cgi-bin.conf

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/codiad\/development-icon.png/' /usr/share/webmin/stabile/index.cgi

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
# Remove tabs from Webmin UI
# rm -r /usr/share/webmin/stabile/tabs/servers

# Install cgi-node
cd /usr/lib/cgi-bin
wget https://github.com/UeiRicho/cgi-node/releases/download/v0.2/cgi-node.js
chmod 755 cgi-node.js
perl -pi -e 's/(\#\!).*/$1\/usr\/bin\/nodejs/' /usr/lib/cgi-bin/cgi-node.js
perl -pi -e 's/(\sSessionPath:).*/$1 "\/var\/nodejs\/sessions"/' /usr/lib/cgi-bin/cgi-node.js
mkdir -p /var/nodejs/sessions
chown www-data:www-data /var/nodejs/sessions

# Prepare stuff for reference stack

# Enable mod_proxy
a2enmod proxy
a2enmod proxy_http

echo "*filter
:INPUT ACCEPT [56:14705]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [56:6504]
-A INPUT ! -s 10.0.0.0/8 -p udp -m udp --dport 12865 -j DROP
-A INPUT ! -s 10.0.0.0/8 -p tcp -m tcp --dport 12865 -j DROP
COMMIT" > /etc/iptables/rules.v4