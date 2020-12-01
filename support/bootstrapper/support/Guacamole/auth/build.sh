#!/bin/sh

mvn package
cp target/guacamole-auth-stabile-0.9.14.jar /etc/guacamole/extensions/ 
cp ../guacamole-index.html /var/lib/tomcat8/webapps/guacamole/index.html
systemctl restart tomcat8

